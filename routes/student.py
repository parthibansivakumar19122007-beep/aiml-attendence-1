from datetime import datetime, date
import pytz
from flask import (Blueprint, render_template, session, redirect,
                   url_for, flash, current_app, request, jsonify)
from models import (db, Student, AttendanceRecord, AttendanceSession,
                    Timetable, Subject, FaceEmbedding)
from services.auth_service import login_required, role_required, get_current_user
from services.timetable_service import get_server_ist_datetime
from services.face_service import verify_face_from_b64, face_recognition_status
from services.location_service import haversine_distance_meters

student_bp = Blueprint('student', __name__, url_prefix='/student')

IST = pytz.timezone('Asia/Kolkata')
GEOFENCE_RADIUS_M = 50


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route('/dashboard')
@role_required('STUDENT')
def dashboard():
    user = get_current_user()
    student = Student.query.filter_by(user_id=user.id).first()

    if not student:
        flash('Student profile not found. Please contact administration.', 'danger')
        return redirect(url_for('auth.logout'))

    ist_now = get_server_ist_datetime()
    today_date = ist_now.date()

    # Today's attendance via join through timetable
    today_records = (
        db.session.query(AttendanceRecord, AttendanceSession, Timetable, Subject)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .outerjoin(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .outerjoin(Subject, Timetable.subject_id == Subject.id)
        .filter(
            AttendanceRecord.student_id == student.id,
            AttendanceSession.date == today_date
        )
        .order_by(AttendanceRecord.scanned_at.asc())
        .all()
    )

    # Overall stats via timetable class_id join
    total_conducted = (
        db.session.query(AttendanceSession)
        .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .filter(
            Timetable.class_id == student.class_id,
            AttendanceSession.status.in_(['CLOSED', 'OPEN'])
        )
        .count()
    )

    total_present = (
        db.session.query(AttendanceRecord)
        .filter(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.status == 'PRESENT'
        )
        .count()
    )

    overall_percentage = round((total_present / total_conducted * 100), 1) if total_conducted > 0 else 100.0

    # Active open sessions for this student's class right now
    open_sessions = (
        db.session.query(AttendanceSession, Timetable, Subject)
        .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .join(Subject, Timetable.subject_id == Subject.id)
        .filter(
            Timetable.class_id == student.class_id,
            AttendanceSession.status == 'OPEN',
            AttendanceSession.date == today_date
        )
        .all()
    )

    # Face enrollment status
    has_face = (
        FaceEmbedding.query
        .filter_by(user_id=user.id, is_active=True)
        .first() is not None
    )

    return render_template(
        'student/dashboard.html',
        student=student,
        today_date=today_date.strftime('%d-%m-%Y'),
        today_day=ist_now.strftime('%A'),
        today_records=today_records,
        total_conducted=total_conducted,
        total_present=total_present,
        overall_percentage=overall_percentage,
        open_sessions=open_sessions,
        has_face=has_face
    )


# ─────────────────────────────────────────────────────────────────────────────
# FACE ATTENDANCE PAGE
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route('/scan')
@role_required('STUDENT')
def scan():
    """Face recognition attendance page."""
    user = get_current_user()
    student = Student.query.filter_by(user_id=user.id).first()

    ist_now = get_server_ist_datetime()
    today_date = ist_now.date()

    # Open sessions for student's class
    open_sessions = (
        db.session.query(AttendanceSession, Timetable, Subject)
        .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .join(Subject, Timetable.subject_id == Subject.id)
        .filter(
            Timetable.class_id == student.class_id,
            AttendanceSession.status == 'OPEN',
            AttendanceSession.date == today_date
        )
        .all()
    )

    # Has face enrolled?
    has_face = (
        FaceEmbedding.query
        .filter_by(user_id=user.id, is_active=True)
        .first() is not None
    )

    face_status = face_recognition_status()

    return render_template(
        'student/scan.html',
        student=student,
        open_sessions=open_sessions,
        has_face=has_face,
        face_status=face_status,
        ist_now=ist_now
    )


@student_bp.route('/api/open-sessions')
@role_required('STUDENT')
def api_open_sessions():
    """Returns JSON list of active open sessions for this student's class."""
    user = get_current_user()
    student = Student.query.filter_by(user_id=user.id).first()
    if not student:
        return jsonify({'sessions': [], 'count': 0})

    ist_now = get_server_ist_datetime()
    today_date = ist_now.date()

    open_sessions = (
        db.session.query(AttendanceSession, Timetable, Subject)
        .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .join(Subject, Timetable.subject_id == Subject.id)
        .filter(
            Timetable.class_id == student.class_id,
            AttendanceSession.status == 'OPEN',
            AttendanceSession.date == today_date
        )
        .all()
    )

    result = []
    for sess, tt, sub in open_sessions:
        fac_name = tt.faculty.user.name if tt.faculty and tt.faculty.user else 'Faculty'
        result.append({
            'id': sess.id,
            'hour_number': tt.hour_number,
            'subject_short': sub.short_name,
            'subject_name': sub.subject_name,
            'faculty_name': fac_name,
            'label': f"Hour {tt.hour_number} – {sub.short_name} ({sub.subject_name}) • Faculty: {fac_name}"
        })

    return jsonify({'sessions': result, 'count': len(result)})


# ─────────────────────────────────────────────────────────────────────────────
# FACE VERIFICATION API
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route('/api/verify-face', methods=['POST'])
@role_required('STUDENT')
def api_verify_face():
    """
    Receives:
      - frame_b64: base64 webcam snapshot
      - session_id: int (AttendanceSession.id)
      - latitude: float (optional)
      - longitude: float (optional)

    Returns JSON: { success, status, message, face_confidence }
    """
    user = get_current_user()
    student = Student.query.filter_by(user_id=user.id).first()

    if not student:
        return jsonify({'success': False, 'status': 'ERROR', 'message': 'Student profile not found.'}), 400

    data = request.get_json() or {}
    frame_b64 = data.get('frame_b64', '')
    session_id = data.get('session_id')
    lat_val = data.get('latitude')
    lng_val = data.get('longitude')

    if not frame_b64:
        return jsonify({'success': False, 'status': 'NO_FRAME', 'message': 'No camera frame received.'}), 400

    if not session_id:
        return jsonify({'success': False, 'status': 'NO_SESSION', 'message': 'No attendance session selected.'}), 400

    # ── Load attendance session ───────────────────────────────────────────────
    att_session = AttendanceSession.query.get(session_id)
    if not att_session:
        return jsonify({'success': False, 'status': 'INVALID_SESSION', 'message': 'Attendance session not found.'}), 400
    if att_session.status != 'OPEN':
        return jsonify({'success': False, 'status': 'SESSION_CLOSED', 'message': 'This session is no longer open.'}), 400

    # Verify this session belongs to the student's class
    timetable_entry = Timetable.query.get(att_session.timetable_id)
    if not timetable_entry or timetable_entry.class_id != student.class_id:
        return jsonify({'success': False, 'status': 'WRONG_CLASS', 'message': 'This session does not belong to your class.'}), 403

    # ── Check already marked ─────────────────────────────────────────────────
    already = AttendanceRecord.query.filter_by(
        session_id=att_session.id, student_id=student.id
    ).first()
    if already and already.status == 'PRESENT':
        return jsonify({
            'success': True,
            'status': 'ALREADY_MARKED',
            'message': 'You have already marked attendance for this session.',
            'face_confidence': float(already.face_confidence) if already.face_confidence else None
        })

    # ── Load student face embedding ───────────────────────────────────────────
    face_emb = FaceEmbedding.query.filter_by(user_id=user.id, is_active=True).first()
    if not face_emb:
        return jsonify({
            'success': False,
            'status': 'NO_FACE_ENROLLED',
            'message': 'Your face is not enrolled. Please contact your administrator.'
        }), 400

    # ── Face Recognition ──────────────────────────────────────────────────────
    is_match, confidence, face_error = verify_face_from_b64(frame_b64, face_emb.embedding_data)

    if not is_match:
        _save_record(att_session.id, student.id, 'REJECTED',
                     face_error or 'Face mismatch',
                     float(lat_val) if lat_val not in (None, '') else None,
                     float(lng_val) if lng_val not in (None, '') else None,
                     None, confidence)
        return jsonify({
            'success': False,
            'status': 'FACE_MISMATCH',
            'message': face_error or 'Face verification failed. Your face does not match the enrolled record.',
            'face_confidence': confidence
        }), 400

    # ── GPS Geofencing (if faculty GPS recorded) ──────────────────────────────
    distance_m = None
    if att_session.faculty_lat and att_session.faculty_lng:
        student_lat = float(lat_val) if lat_val not in (None, '') else None
        student_lng = float(lng_val) if lng_val not in (None, '') else None

        if student_lat is None or student_lng is None:
            return jsonify({
                'success': False,
                'status': 'NO_GPS',
                'message': 'GPS location required. Please allow location access and try again.',
                'face_confidence': confidence
            }), 400

        distance_m = haversine_distance_meters(
            float(att_session.faculty_lat), float(att_session.faculty_lng),
            student_lat, student_lng
        )

        if distance_m > GEOFENCE_RADIUS_M:
            _save_record(att_session.id, student.id, 'REJECTED',
                         f'Outside geofence ({distance_m:.0f}m > {GEOFENCE_RADIUS_M}m)',
                         student_lat, student_lng, distance_m, confidence)
            return jsonify({
                'success': False,
                'status': 'OUTSIDE_GEOFENCE',
                'message': f'You are too far from the classroom ({distance_m:.0f}m). Must be within {GEOFENCE_RADIUS_M}m.',
                'face_confidence': confidence,
                'distance_m': distance_m
            }), 400

    # ── Mark PRESENT ──────────────────────────────────────────────────────────
    student_lat = float(lat_val) if lat_val not in (None, '') else None
    student_lng = float(lng_val) if lng_val not in (None, '') else None

    if already:
        # Update existing rejected record
        already.status = 'PRESENT'
        already.face_confidence = confidence
        already.scanned_at = datetime.now(IST).replace(tzinfo=None)
        already.rejection_reason = None
        if student_lat:
            already.student_lat = student_lat
            already.student_lng = student_lng
            already.distance_m = distance_m
        db.session.commit()
    else:
        _save_record(att_session.id, student.id, 'PRESENT', None,
                     student_lat, student_lng, distance_m, confidence)

    return jsonify({
        'success': True,
        'status': 'PRESENT',
        'message': f'✅ Attendance marked! Face verified with {confidence*100:.0f}% confidence.',
        'face_confidence': confidence
    })


def _save_record(session_id, student_id, status, reason,
                 lat, lng, distance_m, confidence):
    """Helper: create or update an AttendanceRecord."""
    existing = AttendanceRecord.query.filter_by(
        session_id=session_id, student_id=student_id
    ).first()
    if existing:
        existing.status = status
        existing.rejection_reason = reason
        existing.face_confidence = confidence
        existing.scanned_at = datetime.now(IST).replace(tzinfo=None)
    else:
        rec = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            attendance_type='HOURLY_STUDENT',
            scanned_at=datetime.now(IST).replace(tzinfo=None),
            student_lat=lat,
            student_lng=lng,
            distance_m=distance_m,
            face_confidence=confidence,
            status=status,
            rejection_reason=reason
        )
        db.session.add(rec)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# MY ATTENDANCE REPORT
# ─────────────────────────────────────────────────────────────────────────────
@student_bp.route('/attendance')
@role_required('STUDENT')
def attendance():
    user = get_current_user()
    student = Student.query.filter_by(user_id=user.id).first()

    # All subjects for the class (via timetable)
    subjects = (
        db.session.query(Subject)
        .join(Timetable, Timetable.subject_id == Subject.id)
        .filter(Timetable.class_id == student.class_id, Subject.is_active == True)
        .distinct()
        .all()
    )

    subject_stats = []
    for sub in subjects:
        sessions_count = (
            db.session.query(AttendanceSession)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(
                Timetable.subject_id == sub.id,
                Timetable.class_id == student.class_id,
                AttendanceSession.status.in_(['CLOSED', 'OPEN'])
            )
            .count()
        )
        present_count = (
            db.session.query(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(
                Timetable.subject_id == sub.id,
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.status == 'PRESENT'
            )
            .count()
        )
        pct = round((present_count / sessions_count * 100), 1) if sessions_count > 0 else 100.0
        subject_stats.append({
            'code': sub.subject_code,
            'name': sub.subject_name,
            'short_name': sub.short_name,
            'conducted': sessions_count,
            'present': present_count,
            'percentage': pct
        })

    # Recent records
    records_history = (
        db.session.query(AttendanceRecord, AttendanceSession, Timetable, Subject)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .outerjoin(Timetable, AttendanceSession.timetable_id == Timetable.id)
        .outerjoin(Subject, Timetable.subject_id == Subject.id)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceRecord.scanned_at.desc())
        .limit(40)
        .all()
    )

    return render_template(
        'student/attendance.html',
        student=student,
        subject_stats=subject_stats,
        records_history=records_history
    )
