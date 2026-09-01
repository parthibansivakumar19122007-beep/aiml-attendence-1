import io
import csv
from datetime import datetime, date, time
import pytz
from flask import (Blueprint, render_template, session, redirect,
                   url_for, flash, current_app, request, jsonify, Response)
from models import (db, Faculty, Timetable, Subject, AttendanceSession,
                    AttendanceRecord, FacultyAttendance, Student, FaceEmbedding)
from services.auth_service import login_required, role_required, get_current_user
from services.timetable_service import get_current_timetable_session, get_server_ist_datetime
from services.attendance_service import (
    start_faculty_session,
    close_faculty_session,
    get_session_live_feed,
    toggle_record_status,
    auto_expire_stale_sessions,
    process_faculty_face_checkin
)
from services.face_service import face_recognition_status

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')
IST = pytz.timezone('Asia/Kolkata')


# ─────────────────────────────────────────────────────────────────────────────
# FACULTY DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@faculty_bp.route('/dashboard')
@role_required('FACULTY')
def dashboard():
    """Faculty Dashboard displaying faculty profile, morning check-in status, and live/upcoming sessions."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    if not faculty:
        flash('Faculty profile not found. Please contact administration.', 'danger')
        return redirect(url_for('auth.logout'))

    auto_expire_stale_sessions(max_duration_minutes=60)

    ist_now = get_server_ist_datetime()
    
    sim_time_str = request.args.get('sim_time')
    sim_day_str = request.args.get('sim_day')
    
    eval_datetime = ist_now
    if sim_time_str:
        try:
            parts = sim_time_str.split(':')
            eval_time = time(int(parts[0]), int(parts[1]))
            eval_datetime = datetime.combine(ist_now.date(), eval_time)
        except Exception:
            eval_datetime = ist_now

    today_date = ist_now.date()
    today_day = sim_day_str if sim_day_str else ist_now.strftime('%A')

    morning_checkin = FacultyAttendance.query.filter_by(
        faculty_id=faculty.id,
        attendance_date=today_date,
        attendance_type='FACULTY_MORNING',
        status='PRESENT'
    ).first()

    evening_checkin = FacultyAttendance.query.filter_by(
        faculty_id=faculty.id,
        attendance_date=today_date,
        attendance_type='FACULTY_EVENING',
        status='PRESENT'
    ).first()

    today_schedule = Timetable.query.filter_by(
        faculty_id=faculty.id,
        day_of_week=today_day,
        is_active=True
    ).order_by(Timetable.hour_number.asc()).all()

    session_info = get_current_timetable_session(
        faculty.id, 
        target_datetime=eval_datetime,
        target_day=today_day
    )
    current_slot = session_info.get('slot')
    active_session = session_info.get('session')

    # Check if faculty has face enrolled
    has_face = FaceEmbedding.query.filter_by(user_id=user.id, is_active=True).first() is not None

    return render_template(
        'faculty/dashboard.html',
        faculty=faculty,
        today_date=today_date.strftime('%d-%m-%Y'),
        today_day=today_day,
        current_time=eval_datetime.strftime('%I:%M %p'),
        morning_checkin=morning_checkin,
        evening_checkin=evening_checkin,
        today_schedule=today_schedule,
        current_slot=current_slot,
        active_session=active_session,
        session_info=session_info,
        has_face=has_face,
        sim_time=sim_time_str,
        sim_day=sim_day_str
    )


# ─────────────────────────────────────────────────────────────────────────────
# LIVE SESSION VIEW & CONTROL
# ─────────────────────────────────────────────────────────────────────────────
@faculty_bp.route('/session')
@faculty_bp.route('/session/<int:session_id>')
@role_required('FACULTY')
def session_view(session_id=None):
    """Live Attendance Session Control & Real-time Student Face Scans Monitor."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    sim_time_str = request.args.get('sim_time')
    sim_day_str = request.args.get('sim_day')
    
    ist_now = get_server_ist_datetime()
    eval_datetime = ist_now
    if sim_time_str:
        try:
            parts = sim_time_str.split(':')
            eval_time = time(int(parts[0]), int(parts[1]))
            eval_datetime = datetime.combine(ist_now.date(), eval_time)
        except Exception:
            eval_datetime = ist_now

    today_day = sim_day_str if sim_day_str else ist_now.strftime('%A')

    session_info = get_current_timetable_session(
        faculty.id,
        target_datetime=eval_datetime,
        target_day=today_day
    )

    current_slot = session_info.get('slot')
    active_session = None

    if session_id:
        active_session = db.session.get(AttendanceSession, session_id)
    elif session_info.get('session'):
        active_session = session_info['session']

    all_slots = Timetable.query.filter_by(faculty_id=faculty.id, is_active=True).order_by(Timetable.hour_number.asc()).all()
    if not current_slot and all_slots:
        current_slot = all_slots[0]

    return render_template(
        'faculty/session.html',
        faculty=faculty,
        current_slot=current_slot,
        active_session=active_session,
        session_info=session_info,
        all_slots=all_slots,
        sim_time=sim_time_str,
        sim_day=sim_day_str
    )


@faculty_bp.route('/session/start', methods=['POST'])
@role_required('FACULTY')
def start_session():
    """Start an attendance session for the faculty member's current timetable slot."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    lat_val = request.form.get('latitude')
    lng_val = request.form.get('longitude')
    sim_time_str = request.form.get('sim_time')
    sim_day_str = request.form.get('sim_day')
    timetable_id = request.form.get('timetable_id', type=int)

    if not lat_val or not lng_val:
        flash("Unable to capture faculty GPS coordinates. Location is required to start session.", "danger")
        return redirect(url_for('faculty.session_view'))

    try:
        latitude = float(lat_val)
        longitude = float(lng_val)
    except ValueError:
        flash("Invalid GPS coordinates received.", "danger")
        return redirect(url_for('faculty.session_view'))

    eval_datetime = None
    if sim_time_str:
        try:
            parts = sim_time_str.split(':')
            eval_time = time(int(parts[0]), int(parts[1]))
            eval_datetime = datetime.combine(date.today(), eval_time)
        except Exception:
            eval_datetime = None

    session_record, message = start_faculty_session(
        faculty_id=faculty.id,
        latitude=latitude,
        longitude=longitude,
        security_radius_m=50.0,
        target_datetime=eval_datetime,
        target_day=sim_day_str,
        user_id=user.id,
        timetable_id=timetable_id
    )

    if session_record:
        flash(message, 'success')
        return redirect(url_for('faculty.session_view', session_id=session_record.id, sim_time=sim_time_str, sim_day=sim_day_str))
    else:
        flash(message, 'danger')
        return redirect(url_for('faculty.session_view', sim_time=sim_time_str, sim_day=sim_day_str))


@faculty_bp.route('/session/end/<int:session_id>', methods=['POST'])
@role_required('FACULTY')
def end_session(session_id):
    """End and close an active attendance session."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    success, message = close_faculty_session(
        session_id=session_id,
        faculty_id=faculty.id,
        user_id=user.id
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('faculty.dashboard'))


@faculty_bp.route('/session/<int:session_id>/override/<int:record_id>', methods=['POST'])
@role_required('FACULTY')
def override_record(session_id, record_id):
    """Faculty manual override to toggle PRESENT / REJECTED status."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    success, msg, new_status = toggle_record_status(record_id, faculty.id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': success, 'message': msg, 'new_status': new_status})
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('faculty.session_view', session_id=session_id))


@faculty_bp.route('/session/<int:session_id>/export-csv')
@role_required('FACULTY')
def export_session_csv(session_id):
    """Export single session attendance report as CSV."""
    faculty = Faculty.query.filter_by(user_id=session['user_id']).first()
    sess = db.session.get(AttendanceSession, session_id)
    if not sess or sess.faculty_id != faculty.id:
        flash("Session not found or unauthorized.", "danger")
        return redirect(url_for('faculty.dashboard'))

    records = AttendanceRecord.query.filter_by(session_id=session_id).order_by(AttendanceRecord.scanned_at.asc()).all()
    sub_code = sess.timetable_entry.subject.subject_code if sess.timetable_entry and sess.timetable_entry.subject else 'ATT'

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Session ID', 'Date', 'Hour', 'Subject', 'Student Roll No', 'Student Name', 'Status', 'Verified At', 'Distance (m)', 'Face Confidence'])

    for r in records:
        writer.writerow([
            sess.id,
            sess.date.strftime('%d-%m-%Y') if sess.date else '',
            sess.timetable_entry.hour_number if sess.timetable_entry else '',
            sess.timetable_entry.subject.short_name if sess.timetable_entry and sess.timetable_entry.subject else '',
            r.student.student_id if r.student else '',
            r.student.user.name if (r.student and r.student.user) else '',
            r.status,
            r.scanned_at.strftime('%I:%M:%S %p') if r.scanned_at else '',
            f"{float(r.distance_m):.1f}" if r.distance_m is not None else 'N/A',
            f"{float(r.face_confidence)*100:.1f}%" if r.face_confidence is not None else 'N/A'
        ])

    output.seek(0)
    filename = f"Attendance_{sub_code}_{sess.date.strftime('%Y%m%d')}_H{sess.timetable_entry.hour_number if sess.timetable_entry else 'X'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@faculty_bp.route('/api/session/<int:session_id>/live-feed')
@role_required('FACULTY')
def api_session_live_feed(session_id):
    """Live JSON API returning verified student scans and real-time attendance counts."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()

    feed_data = get_session_live_feed(session_id=session_id, faculty_id=faculty.id)
    return jsonify(feed_data)


@faculty_bp.route('/api/current-session')
@role_required('FACULTY')
def api_current_session():
    """Live JSON API for detecting faculty current scheduled session."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()
    if not faculty:
        return jsonify({'error': 'Faculty profile not found'}), 404

    sim_time_str = request.args.get('sim_time')
    sim_day_str = request.args.get('sim_day')
    
    eval_datetime = None
    if sim_time_str:
        try:
            parts = sim_time_str.split(':')
            eval_time = time(int(parts[0]), int(parts[1]))
            eval_datetime = datetime.combine(date.today(), eval_time)
        except Exception:
            eval_datetime = None

    session_info = get_current_timetable_session(
        faculty_id=faculty.id,
        target_datetime=eval_datetime,
        target_day=sim_day_str
    )

    return jsonify({
        'is_scheduled': session_info.get('is_scheduled', False),
        'message': session_info.get('message', ''),
        'server_time': session_info.get('server_time', ''),
        'server_date': session_info.get('server_date', ''),
        'day_of_week': session_info.get('day_of_week', ''),
        'slot': session_info['slot'].to_dict() if session_info.get('slot') else None,
        'session_status': session_info.get('session_status', 'NOT_STARTED')
    })



# ─────────────────────────────────────────────────────────────────────────────
# FACULTY FACE CHECK-IN
# ─────────────────────────────────────────────────────────────────────────────
@faculty_bp.route('/scan')
@role_required('FACULTY')
def scan():
    """Faculty Face Recognition Arrival / Departure Check-in View."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()
    has_face = FaceEmbedding.query.filter_by(user_id=user.id, is_active=True).first() is not None
    face_status = face_recognition_status()
    ist_now = get_server_ist_datetime()

    return render_template(
        'faculty/scan.html',
        faculty=faculty,
        has_face=has_face,
        face_status=face_status,
        ist_now=ist_now
    )


@faculty_bp.route('/api/checkin', methods=['POST'])
@role_required('FACULTY')
def api_faculty_checkin():
    """
    Receives base64 webcam frame and GPS coordinates,
    records FACULTY_MORNING or FACULTY_EVENING via Face Recognition.
    """
    user = get_current_user()
    data = request.get_json() or {}

    frame_b64 = data.get('frame_b64', '')
    lat_val = data.get('latitude')
    lng_val = data.get('longitude')
    force_type = data.get('type') # 'FACULTY_MORNING' or 'FACULTY_EVENING'

    if not frame_b64:
        return jsonify({
            'success': False,
            'status': 'REJECTED',
            'error_code': 'NO_FRAME',
            'message': 'No camera image frame was received.'
        }), 400

    latitude = float(lat_val) if (lat_val is not None and lat_val != '') else None
    longitude = float(lng_val) if (lng_val is not None and lng_val != '') else None

    result = process_faculty_face_checkin(
        logged_in_user_id=user.id,
        frame_b64=frame_b64,
        latitude=latitude,
        longitude=longitude,
        force_type=force_type
    )

    status_code = 200 if result['success'] else (400 if result.get('status') in ['FACE_MISMATCH', 'NO_FACE_ENROLLED'] else 200)
    return jsonify(result), status_code


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@faculty_bp.route('/attendance')
@role_required('FACULTY')
def attendance():
    """Faculty History of conducted sessions and self-attendance log."""
    user = get_current_user()
    faculty = Faculty.query.filter_by(user_id=user.id).first()
    
    self_attendance = FacultyAttendance.query.filter_by(faculty_id=faculty.id)\
        .order_by(FacultyAttendance.attendance_date.desc()).limit(30).all()

    conducted_sessions = AttendanceSession.query.filter_by(faculty_id=faculty.id)\
        .order_by(AttendanceSession.date.desc(), AttendanceSession.opened_at.desc()).limit(30).all()

    return render_template(
        'faculty/attendance.html',
        faculty=faculty,
        self_attendance=self_attendance,
        conducted_sessions=conducted_sessions
    )
