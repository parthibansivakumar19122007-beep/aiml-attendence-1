import io
import csv
from datetime import datetime, date
import pytz
from flask import (Blueprint, render_template, session, redirect,
                   url_for, flash, current_app, request, jsonify, Response)
from models import (db, User, Faculty, Student, Subject, ClassRoom,
                    Timetable, AttendanceSession, AttendanceRecord, FacultyAttendance)
from services.auth_service import login_required, role_required, get_current_user
from services.timetable_service import (
    add_timetable_slot,
    update_timetable_slot,
    delete_timetable_slot,
    toggle_timetable_slot_status,
    get_server_ist_datetime
)
from services.icampus_service import get_icampus_status

hod_bp = Blueprint('hod', __name__, url_prefix='/hod')
IST = pytz.timezone('Asia/Kolkata')


# ─────────────────────────────────────────────────────────────────────────────
# HOD DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@hod_bp.route('/dashboard')
@role_required('HOD')
def dashboard():
    """HOD Executive Dashboard showing live timetable status matrix for today and overall department metrics."""
    user = get_current_user()
    ist_now = get_server_ist_datetime()
    today_date = ist_now.date()
    today_day = ist_now.strftime('%A')

    primary_class = ClassRoom.query.first()
    
    today_slots = Timetable.query.filter_by(
        class_id=primary_class.id if primary_class else 1,
        day_of_week=today_day,
        is_active=True
    ).order_by(Timetable.hour_number.asc()).all()

    hour_matrix = []
    total_students_enrolled = Student.query.filter_by(class_id=primary_class.id if primary_class else 1).count()

    for slot in today_slots:
        session_record = AttendanceSession.query.filter_by(
            timetable_id=slot.id,
            date=today_date
        ).first()

        status = 'PENDING'
        present_count = 0
        
        if session_record:
            if session_record.status in ['CLOSED', 'EXPIRED']:
                status = 'COMPLETED'
            elif session_record.status == 'OPEN':
                status = 'IN_PROGRESS'
            
            present_count = AttendanceRecord.query.filter_by(
                session_id=session_record.id,
                status='PRESENT'
            ).count()

        hour_matrix.append({
            'slot': slot,
            'session': session_record,
            'status': status,
            'present_count': present_count,
            'total_students': total_students_enrolled,
            'attendance_pct': round((present_count / total_students_enrolled * 100), 1) if total_students_enrolled > 0 else 0
        })

    faculty_count = Faculty.query.count()
    student_count = Student.query.count()
    subject_count = Subject.query.count()

    faculty_morning_count = FacultyAttendance.query.filter_by(
        attendance_date=today_date,
        attendance_type='FACULTY_MORNING',
        status='PRESENT'
    ).count()

    return render_template(
        'hod/dashboard.html',
        user=user,
        today_date=today_date.strftime('%d-%m-%Y'),
        today_day=today_day,
        current_time=ist_now.strftime('%I:%M %p'),
        primary_class=primary_class,
        hour_matrix=hour_matrix,
        faculty_count=faculty_count,
        student_count=student_count,
        subject_count=subject_count,
        faculty_morning_count=faculty_morning_count
    )


# ─────────────────────────────────────────────────────────────────────────────
# SESSION DETAILS DRILL-DOWN API
# ─────────────────────────────────────────────────────────────────────────────
@hod_bp.route('/api/session-details/<int:session_id>')
@role_required('HOD')
def api_session_details(session_id):
    """Returns student-wise drill-down for any selected session in the HOD matrix."""
    session_record = db.session.get(AttendanceSession, session_id)
    if not session_record:
        return jsonify({'error': 'Session not found'}), 404

    records = AttendanceRecord.query.filter_by(session_id=session_id).order_by(AttendanceRecord.scanned_at.asc()).all()
    records_data = []

    for r in records:
        records_data.append({
            'student_id': r.student.student_id if r.student else '',
            'student_name': r.student.user.name if (r.student and r.student.user) else '',
            'scanned_at': r.scanned_at.strftime('%I:%M:%S %p') if r.scanned_at else '',
            'distance_m': float(r.distance_m) if r.distance_m is not None else None,
            'face_confidence': float(r.face_confidence) if r.face_confidence is not None else None,
            'status': r.status,
            'rejection_reason': r.rejection_reason
        })

    return jsonify({
        'session_id': session_record.id,
        'subject_name': session_record.timetable_entry.subject.subject_name if session_record.timetable_entry and session_record.timetable_entry.subject else 'General',
        'subject_short': session_record.timetable_entry.subject.short_name if session_record.timetable_entry and session_record.timetable_entry.subject else '',
        'hour_number': session_record.timetable_entry.hour_number if session_record.timetable_entry else None,
        'faculty_name': session_record.faculty.user.name if session_record.faculty and session_record.faculty.user else 'N/A',
        'session_date': session_record.date.strftime('%d-%m-%Y') if session_record.date else '',
        'opened_at': session_record.opened_at.strftime('%I:%M %p') if session_record.opened_at else '',
        'closed_at': session_record.closed_at.strftime('%I:%M %p') if session_record.closed_at else 'Active',
        'status': session_record.status,
        'total_scanned': len(records_data),
        'records': records_data
    })


# ─────────────────────────────────────────────────────────────────────────────
# TIMETABLE MASTER CRUD
# ─────────────────────────────────────────────────────────────────────────────
@hod_bp.route('/timetable', methods=['GET'])
@role_required('HOD', 'ADMIN')
def timetable():
    """HOD Timetable Master View with filtering, add, edit, and delete actions."""
    filter_day = request.args.get('day', '')
    filter_faculty = request.args.get('faculty_id', '')

    query = Timetable.query

    if filter_day:
        query = query.filter_by(day_of_week=filter_day)
    if filter_faculty and filter_faculty.isdigit():
        query = query.filter_by(faculty_id=int(filter_faculty))

    all_slots = query.order_by(
        Timetable.day_of_week.asc(),
        Timetable.hour_number.asc()
    ).all()

    classes = ClassRoom.query.all()
    faculty_list = Faculty.query.all()
    subjects_list = Subject.query.filter_by(is_active=True).order_by(Subject.short_name.asc()).all()

    return render_template(
        'hod/timetable.html',
        classes=classes,
        faculty_list=faculty_list,
        subjects_list=subjects_list,
        all_slots=all_slots,
        filter_day=filter_day,
        filter_faculty=int(filter_faculty) if filter_faculty.isdigit() else None
    )


@hod_bp.route('/timetable/add', methods=['POST'])
@role_required('HOD', 'ADMIN')
def add_timetable():
    """Handle adding a new Timetable slot."""
    user = get_current_user()
    try:
        class_id = int(request.form.get('class_id', 1))
        day_of_week = request.form.get('day_of_week')
        hour_number = int(request.form.get('hour_number'))
        subject_id = int(request.form.get('subject_id'))
        faculty_id = int(request.form.get('faculty_id'))
        academic_year = request.form.get('academic_year', '2026-2027')
        start_time_val = request.form.get('start_time')
        end_time_val = request.form.get('end_time')
        is_active = True if request.form.get('is_active') == 'on' else False

        slot, message = add_timetable_slot(
            class_id=class_id,
            day_of_week=day_of_week,
            hour_number=hour_number,
            subject_id=subject_id,
            faculty_id=faculty_id,
            academic_year=academic_year,
            start_time_val=start_time_val,
            end_time_val=end_time_val,
            is_active=is_active,
            user_id=user.id if user else None
        )

        if slot:
            flash(message, 'success')
        else:
            flash(message, 'danger')

    except Exception as e:
        flash(f"Error creating timetable slot: {str(e)}", 'danger')

    return redirect(url_for('hod.timetable'))


@hod_bp.route('/timetable/edit/<int:slot_id>', methods=['POST'])
@role_required('HOD', 'ADMIN')
def edit_timetable(slot_id):
    """Handle updating an existing Timetable slot."""
    user = get_current_user()
    try:
        class_id = int(request.form.get('class_id', 1))
        day_of_week = request.form.get('day_of_week')
        hour_number = int(request.form.get('hour_number'))
        subject_id = int(request.form.get('subject_id'))
        faculty_id = int(request.form.get('faculty_id'))
        academic_year = request.form.get('academic_year', '2026-2027')
        start_time_val = request.form.get('start_time')
        end_time_val = request.form.get('end_time')
        is_active = True if request.form.get('is_active') == 'on' else False

        slot, message = update_timetable_slot(
            slot_id=slot_id,
            class_id=class_id,
            day_of_week=day_of_week,
            hour_number=hour_number,
            subject_id=subject_id,
            faculty_id=faculty_id,
            academic_year=academic_year,
            start_time_val=start_time_val,
            end_time_val=end_time_val,
            is_active=is_active,
            user_id=user.id if user else None
        )

        if slot:
            flash(message, 'success')
        else:
            flash(message, 'danger')

    except Exception as e:
        flash(f"Error updating timetable slot: {str(e)}", 'danger')

    return redirect(url_for('hod.timetable'))


@hod_bp.route('/timetable/delete/<int:slot_id>', methods=['POST'])
@role_required('HOD', 'ADMIN')
def delete_timetable(slot_id):
    """Handle deleting a Timetable slot."""
    user = get_current_user()
    success, message = delete_timetable_slot(slot_id=slot_id, user_id=user.id if user else None)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('hod.timetable'))


@hod_bp.route('/timetable/toggle/<int:slot_id>', methods=['POST'])
@role_required('HOD', 'ADMIN')
def toggle_timetable(slot_id):
    """Toggle active/inactive status of a Timetable slot."""
    user = get_current_user()
    success, message = toggle_timetable_slot_status(slot_id=slot_id, user_id=user.id if user else None)
    if success:
        flash(message, 'info')
    else:
        flash(message, 'danger')
    return redirect(url_for('hod.timetable'))


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE AUDIT & HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@hod_bp.route('/attendance')
@role_required('HOD')
def attendance():
    """HOD Detailed Attendance Monitor & Filter."""
    selected_date_str = request.args.get('date')
    ist_now = get_server_ist_datetime()
    
    if selected_date_str:
        try:
            filter_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = ist_now.date()
    else:
        filter_date = ist_now.date()

    sessions = AttendanceSession.query.filter_by(date=filter_date)\
        .order_by(AttendanceSession.opened_at.desc()).all()

    faculty_attendances = FacultyAttendance.query.filter_by(attendance_date=filter_date)\
        .order_by(FacultyAttendance.scanned_at.asc()).all()

    return render_template(
        'hod/attendance.html',
        filter_date=filter_date.strftime('%Y-%m-%d'),
        sessions=sessions,
        faculty_attendances=faculty_attendances
    )


# ─────────────────────────────────────────────────────────────────────────────
# COMPREHENSIVE REPORTS & ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
@hod_bp.route('/reports')
@role_required('HOD')
def reports():
    """HOD Comprehensive Analytics & Subject-wise Reports."""
    students = Student.query.all()
    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.short_name.asc()).all()
    
    student_reports = []
    for st in students:
        total_sessions = (
            db.session.query(AttendanceSession)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(Timetable.class_id == st.class_id, AttendanceSession.status.in_(['CLOSED', 'OPEN']))
            .count()
        )
        attended = AttendanceRecord.query.filter_by(student_id=st.id, status='PRESENT').count()
        pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 100.0
        student_reports.append({
            'student': st,
            'total_sessions': total_sessions,
            'attended': attended,
            'percentage': pct
        })

    subject_analytics = []
    for sub in subjects:
        total_conducted = (
            db.session.query(AttendanceSession)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(Timetable.subject_id == sub.id, AttendanceSession.status.in_(['CLOSED', 'OPEN']))
            .count()
        )
        
        total_present_scans = (
            db.session.query(AttendanceRecord)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(Timetable.subject_id == sub.id, AttendanceRecord.status == 'PRESENT')
            .count()
        )

        total_expected = total_conducted * len(students) if len(students) > 0 else 0
        overall_sub_pct = round((total_present_scans / total_expected * 100), 1) if total_expected > 0 else 100.0

        subject_analytics.append({
            'subject': sub,
            'conducted_hours': total_conducted,
            'present_scans': total_present_scans,
            'average_percentage': overall_sub_pct
        })

    icampus_info = get_icampus_status()

    return render_template(
        'hod/reports.html',
        student_reports=student_reports,
        subject_analytics=subject_analytics,
        subjects=subjects,
        icampus_info=icampus_info
    )


@hod_bp.route('/reports/export-csv')
@role_required('HOD')
def export_reports_csv():
    """Generates and downloads official Attendance CSV Report."""
    students = Student.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV Header
    writer.writerow([
        'Student ID', 
        'Student Name', 
        'Email', 
        'Class', 
        'Section', 
        'Total Sessions Conducted', 
        'Sessions Attended', 
        'Attendance Percentage', 
        'Eligibility Status (>=75%)'
    ])

    for st in students:
        total_sessions = (
            db.session.query(AttendanceSession)
            .join(Timetable, AttendanceSession.timetable_id == Timetable.id)
            .filter(Timetable.class_id == st.class_id, AttendanceSession.status.in_(['CLOSED', 'OPEN']))
            .count()
        )
        attended = AttendanceRecord.query.filter_by(student_id=st.id, status='PRESENT').count()
        pct = round((attended / total_sessions * 100), 1) if total_sessions > 0 else 100.0
        status = 'ELIGIBLE' if pct >= 75.0 else 'SHORTAGE'

        writer.writerow([
            st.student_id,
            st.user.name if st.user else '',
            st.user.email if st.user else '',
            st.classroom.class_name if st.classroom else '',
            st.section,
            total_sessions,
            attended,
            f"{pct}%",
            status
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=AIML_Attendance_Report_2026.csv"}
    )
