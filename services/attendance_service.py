"""
Attendance Service
Handles faculty session lifecycles, live feed aggregation,
student face attendance processing, faculty face check-ins,
manual overrides, and stale session auto-expiry.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple, Dict, Any, List
import pytz
from models import (
    db, 
    AttendanceSession, 
    AttendanceRecord, 
    FacultyAttendance, 
    Timetable, 
    Faculty, 
    Student, 
    User, 
    AuditLog,
    ClassRoom,
    FaceEmbedding
)
from services.timetable_service import get_server_ist_datetime, get_current_timetable_session
from services.location_service import verify_geofence_proximity, haversine_distance_meters
from services.face_service import verify_face_from_b64
from services.barcode_service import (
    identify_student_by_barcode,
    identify_faculty_by_barcode,
    validate_student_id_card_ownership
)

IST = pytz.timezone('Asia/Kolkata')
GEOFENCE_RADIUS_M = 50.0

def start_faculty_session(
    faculty_id: int,
    latitude: float,
    longitude: float,
    security_radius_m: float = 50.0,
    target_datetime: Optional[datetime] = None,
    target_day: Optional[str] = None,
    user_id: Optional[int] = None,
    timetable_id: Optional[int] = None
) -> Tuple[Optional[AttendanceSession], str]:
    """Starts an attendance session for the faculty member's currently scheduled class."""
    if latitude is None or longitude is None:
        return None, "GPS coordinates are mandatory to establish the geofence reference center."

    slot = None
    if timetable_id:
        slot = Timetable.query.filter_by(id=timetable_id, is_active=True).first()
    else:
        session_info = get_current_timetable_session(
            faculty_id=faculty_id,
            target_datetime=target_datetime,
            target_day=target_day
        )
        if not session_info.get('is_scheduled') or not session_info.get('slot'):
            return None, session_info.get('message', "You are not scheduled to handle a class at this time.")
        slot = session_info['slot']

    if not slot:
        return None, "No active timetable slot found."

    ist_now = target_datetime or get_server_ist_datetime()
    current_date = ist_now.date()

    existing_session = AttendanceSession.query.filter_by(
        timetable_id=slot.id,
        date=current_date
    ).first()

    if existing_session:
        if existing_session.status == 'OPEN':
            return existing_session, "Attendance session is already open and active."
        elif existing_session.status in ['CLOSED', 'EXPIRED']:
            # Reopen the session so faculty can re-conduct or resume attendance
            existing_session.status = 'OPEN'
            existing_session.faculty_lat = latitude
            existing_session.faculty_lng = longitude
            existing_session.opened_at = ist_now
            db.session.commit()
            sub_name = slot.subject.short_name if slot.subject else 'Class'
            return existing_session, f"Attendance session for {sub_name} (Hour {slot.hour_number}) reopened and active."

    try:
        session_record = AttendanceSession(
            timetable_id=slot.id,
            faculty_id=faculty_id,
            date=current_date,
            faculty_lat=latitude,
            faculty_lng=longitude,
            opened_at=ist_now,
            status='OPEN'
        )
        db.session.add(session_record)
        db.session.flush()

        if user_id:
            sub_short = slot.subject.short_name if slot.subject else 'Class'
            log = AuditLog(
                user_id=user_id,
                action='FACULTY_STARTED_SESSION',
                details=f"Faculty ID:{faculty_id} opened session ID:{session_record.id} for Slot:{slot.id} ({sub_short}) at GPS ({latitude:.5f}, {longitude:.5f})"
            )
            db.session.add(log)

        db.session.commit()
        sub_name = slot.subject.short_name if slot.subject else 'Slot'
        return session_record, f"Attendance session for {sub_name} (Hour {slot.hour_number}) started successfully."
    except Exception as e:
        db.session.rollback()
        return None, f"Database error starting session: {str(e)}"


def close_faculty_session(
    session_id: int,
    faculty_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Tuple[bool, str]:
    """Closes an active attendance session, preventing further student scans."""
    session_record = db.session.get(AttendanceSession, session_id)
    if not session_record:
        return False, "Attendance session not found."

    if faculty_id and session_record.faculty_id != faculty_id:
        return False, "Unauthorized: You can only close attendance sessions started by your account."

    if session_record.status != 'OPEN':
        return False, f"Session is already {session_record.status}."

    ist_now = get_server_ist_datetime()
    try:
        session_record.status = 'CLOSED'
        session_record.closed_at = ist_now

        if user_id:
            present_count = AttendanceRecord.query.filter_by(
                session_id=session_id,
                status='PRESENT'
            ).count()
            log = AuditLog(
                user_id=user_id,
                action='FACULTY_CLOSED_SESSION',
                details=f"Closed session ID:{session_id}. Total students present: {present_count}"
            )
            db.session.add(log)

        db.session.commit()
        return True, "Attendance session closed successfully. No further face scans will be accepted."
    except Exception as e:
        db.session.rollback()
        return False, f"Database error closing session: {str(e)}"


def get_session_live_feed(
    session_id: int,
    faculty_id: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieves live real-time status and verified student face scans for an attendance session."""
    session_record = db.session.get(AttendanceSession, session_id)
    if not session_record:
        return {'error': 'Session not found'}

    if faculty_id and session_record.faculty_id != faculty_id:
        return {'error': 'Unauthorized access to session feed'}

    records = AttendanceRecord.query.filter_by(session_id=session_id)\
        .order_by(AttendanceRecord.scanned_at.desc()).all()

    records_data = []
    present_count = 0
    rejected_count = 0

    for r in records:
        if r.status == 'PRESENT':
            present_count += 1
        else:
            rejected_count += 1

        records_data.append({
            'id': r.id,
            'student_id': r.student.student_id if r.student else '',
            'student_name': r.student.user.name if (r.student and r.student.user) else '',
            'scanned_at': r.scanned_at.strftime('%I:%M:%S %p') if r.scanned_at else '',
            'distance_m': float(r.distance_m) if r.distance_m is not None else None,
            'face_confidence': float(r.face_confidence) if r.face_confidence is not None else None,
            'status': r.status,
            'rejection_reason': r.rejection_reason
        })

    slot_info = session_record.timetable_entry.to_dict() if session_record.timetable_entry else None
    
    # Calculate attendance percentage based on total students in class
    class_id = session_record.timetable_entry.class_id if session_record.timetable_entry else None
    total_class_students = Student.query.filter_by(class_id=class_id).count() if class_id else len(records)
    attendance_pct = round((present_count / total_class_students * 100), 1) if total_class_students > 0 else 0

    return {
        'session_id': session_record.id,
        'status': session_record.status,
        'opened_at': session_record.opened_at.strftime('%I:%M %p') if session_record.opened_at else '',
        'closed_at': session_record.closed_at.strftime('%I:%M %p') if session_record.closed_at else None,
        'faculty_lat': float(session_record.faculty_lat) if session_record.faculty_lat is not None else None,
        'faculty_lng': float(session_record.faculty_lng) if session_record.faculty_lng is not None else None,
        'security_radius_m': GEOFENCE_RADIUS_M,
        'slot': slot_info,
        'present_count': present_count,
        'rejected_count': rejected_count,
        'total_scans': len(records),
        'total_class_students': total_class_students,
        'attendance_pct': attendance_pct,
        'records': records_data
    }


def toggle_record_status(record_id: int, faculty_id: int) -> Tuple[bool, str, Optional[str]]:
    """Allows faculty to manually override student attendance status (PRESENT <-> REJECTED)."""
    rec = db.session.get(AttendanceRecord, record_id)
    if not rec:
        return False, "Attendance record not found.", None

    if rec.session and rec.session.faculty_id != faculty_id:
        return False, "Unauthorized: Record does not belong to your session.", None

    new_status = 'REJECTED' if rec.status == 'PRESENT' else 'PRESENT'
    old_status = rec.status
    rec.status = new_status
    if new_status == 'PRESENT':
        rec.rejection_reason = "Manually approved by faculty"
    else:
        rec.rejection_reason = "Manually revoked by faculty"

    try:
        faculty_obj = db.session.get(Faculty, faculty_id)
        log = AuditLog(
            user_id=faculty_obj.user_id if faculty_obj else None,
            action='FACULTY_MANUAL_OVERRIDE',
            details=f"Overrode record ID:{rec.id} for Student {rec.student.student_id if rec.student else ''} from {old_status} to {new_status}"
        )
        db.session.add(log)
        db.session.commit()
        return True, f"Status updated to {new_status} for {rec.student.user.name if rec.student and rec.student.user else ''}", new_status
    except Exception as e:
        db.session.rollback()
        return False, f"Database error: {str(e)}", None


def auto_expire_stale_sessions(max_duration_minutes: int = 60) -> int:
    """Finds and automatically marks lingering OPEN sessions as EXPIRED."""
    ist_now = get_server_ist_datetime()
    cutoff_time = ist_now - timedelta(minutes=max_duration_minutes)
    
    stale_sessions = AttendanceSession.query.filter(
        AttendanceSession.status == 'OPEN',
        AttendanceSession.opened_at <= cutoff_time
    ).all()

    count = 0
    for sess in stale_sessions:
        sess.status = 'EXPIRED'
        sess.closed_at = ist_now
        count += 1

    if count > 0:
        db.session.commit()
    return count


def process_faculty_face_checkin(
    logged_in_user_id: int,
    frame_b64: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    force_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handles Faculty Face Recognition Check-in (Morning & Evening arrival/departure).
    """
    ist_now = get_server_ist_datetime()
    current_date = ist_now.date()
    current_time_obj = ist_now.time()

    faculty = Faculty.query.filter_by(user_id=logged_in_user_id).first()
    if not faculty:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'ROLE_DENIED',
            'message': "Access denied: Only faculty members can record faculty arrival/departure."
        }

    # Check enrolled face
    face_emb = FaceEmbedding.query.filter_by(user_id=logged_in_user_id, is_active=True).first()
    if not face_emb:
        return {
            'success': False,
            'status': 'NO_FACE_ENROLLED',
            'message': "Your face is not enrolled. Please contact administration to register your face."
        }

    # Determine type
    if force_type in ['FACULTY_MORNING', 'FACULTY_EVENING']:
        att_type = force_type
    else:
        att_type = 'FACULTY_MORNING' if current_time_obj < time(13, 0) else 'FACULTY_EVENING'

    type_label = "Morning Check-in" if att_type == 'FACULTY_MORNING' else "Evening Check-out"

    # Duplicate check
    existing_entry = FacultyAttendance.query.filter_by(
        faculty_id=faculty.id,
        attendance_date=current_date,
        attendance_type=att_type
    ).first()

    if existing_entry and existing_entry.status == 'PRESENT':
        return {
            'success': False,
            'status': 'DUPLICATE',
            'error_code': 'FACULTY_DUPLICATE',
            'attendance_type': att_type,
            'message': f"{type_label} already recorded for today at {existing_entry.scanned_at.strftime('%I:%M %p')}."
        }

    # Face verification
    is_match, confidence, error_msg = verify_face_from_b64(frame_b64, face_emb.embedding_data)
    if not is_match:
        return {
            'success': False,
            'status': 'FACE_MISMATCH',
            'confidence': confidence,
            'message': error_msg or "Face verification failed. Please align your face with the camera."
        }

    try:
        rec = FacultyAttendance(
            faculty_id=faculty.id,
            attendance_date=current_date,
            attendance_type=att_type,
            scanned_at=ist_now,
            latitude=latitude,
            longitude=longitude,
            status='PRESENT'
        )
        db.session.add(rec)

        log = AuditLog(
            user_id=logged_in_user_id,
            action=f'{att_type}_FACE_VERIFIED',
            details=f"Faculty {faculty.faculty_id} ({faculty.user.name}) recorded {att_type} via Face Recognition (Conf: {confidence*100:.1f}%)"
        )
        db.session.add(log)
        db.session.commit()

        return {
            'success': True,
            'status': 'PRESENT',
            'attendance_type': att_type,
            'type_label': type_label,
            'faculty_name': faculty.user.name,
            'faculty_id': faculty.faculty_id,
            'confidence': confidence,
            'date': current_date.strftime('%d-%m-%Y'),
            'scanned_at': ist_now.strftime('%I:%M:%S %p'),
            'message': f"✅ {type_label} successful! Face verified ({confidence*100:.0f}% confidence)."
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'status': 'ERROR',
            'message': f"Database error recording faculty attendance: {str(e)}"
        }


def process_student_hourly_attendance(
    logged_in_user_id: int,
    scanned_barcode: str,
    student_lat: Optional[float] = None,
    student_lng: Optional[float] = None,
    target_session_id: Optional[int] = None,
    target_datetime: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Validates and marks hourly student attendance using ID badge barcode/QR and GPS proximity.
    """
    # 1. Verify anti-proxy ID badge ownership
    is_owner, student, badge_msg = validate_student_id_card_ownership(logged_in_user_id, scanned_barcode)
    if not is_owner:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'INVALID_BADGE',
            'message': badge_msg
        }

    # 2. Verify GPS location availability
    if student_lat is None or student_lng is None:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'LOCATION_UNAVAILABLE',
            'message': 'Location permission denied: GPS coordinates are required for verification.'
        }

    ist_now = target_datetime or get_server_ist_datetime()
    current_date = ist_now.date()

    # 3. Resolve attendance session
    if target_session_id:
        sess = db.session.get(AttendanceSession, target_session_id)
    else:
        sess = AttendanceSession.query.join(Timetable, AttendanceSession.timetable_id == Timetable.id).filter(
            Timetable.class_id == student.class_id,
            AttendanceSession.status == 'OPEN',
            AttendanceSession.date == current_date
        ).first()

    if not sess:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'NO_SESSION',
            'message': 'No active attendance session found for your class.'
        }

    if sess.status != 'OPEN':
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'SESSION_CLOSED',
            'message': 'Attendance session is closed. No further scans are accepted.'
        }

    # 4. Check duplicate scan
    existing_rec = AttendanceRecord.query.filter_by(
        session_id=sess.id,
        student_id=student.id
    ).first()

    if existing_rec and existing_rec.status == 'PRESENT':
        return {
            'success': False,
            'status': 'DUPLICATE',
            'error_code': 'DUPLICATE',
            'message': f'Attendance already marked for this session at {existing_rec.scanned_at.strftime("%I:%M %p")}.'
        }

    # 5. Geofence verification
    distance_m = 0.0
    if sess.faculty_lat is not None and sess.faculty_lng is not None:
        distance_m = haversine_distance_meters(
            float(sess.faculty_lat), float(sess.faculty_lng),
            float(student_lat), float(student_lng)
        )
        if distance_m > GEOFENCE_RADIUS_M:
            return {
                'success': False,
                'status': 'REJECTED',
                'error_code': 'OUTSIDE_GEOFENCE',
                'distance_m': distance_m,
                'message': f'Attendance rejected: You are outside the 50-meter attendance area ({distance_m:.1f}m away).'
            }

    # 6. Record PRESENT attendance
    try:
        if existing_rec:
            existing_rec.status = 'PRESENT'
            existing_rec.rejection_reason = None
            existing_rec.scanned_at = ist_now
            existing_rec.student_lat = student_lat
            existing_rec.student_lng = student_lng
            existing_rec.distance_m = distance_m
        else:
            rec = AttendanceRecord(
                session_id=sess.id,
                student_id=student.id,
                attendance_type='HOURLY_STUDENT',
                scanned_at=ist_now,
                student_lat=student_lat,
                student_lng=student_lng,
                distance_m=distance_m,
                status='PRESENT'
            )
            db.session.add(rec)

        log = AuditLog(
            user_id=logged_in_user_id,
            action='STUDENT_SCANNED_ATTENDANCE',
            details=f"Student {student.student_id} marked PRESENT for Session ID:{sess.id} (Distance: {distance_m:.1f}m)"
        )
        db.session.add(log)
        db.session.commit()

        return {
            'success': True,
            'status': 'PRESENT',
            'distance_m': distance_m,
            'message': f'Attendance marked PRESENT ✓ ({student.user.name})'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'status': 'ERROR',
            'message': f'Database error: {str(e)}'
        }


def process_student_morning_attendance(
    logged_in_user_id: int,
    scanned_barcode: str,
    student_lat: Optional[float] = None,
    student_lng: Optional[float] = None,
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Records student morning arrival check-in.
    """
    is_owner, student, badge_msg = validate_student_id_card_ownership(logged_in_user_id, scanned_barcode)
    if not is_owner:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'INVALID_BADGE',
            'message': badge_msg
        }

    ist_now = get_server_ist_datetime()
    check_date = target_date if target_date else ist_now.date()
    scanned_dt = datetime.combine(check_date, time(9, 0)) if target_date else ist_now

    existing = AttendanceRecord.query.filter(
        AttendanceRecord.student_id == student.id,
        AttendanceRecord.attendance_type == 'MORNING_STUDENT',
        db.func.date(AttendanceRecord.scanned_at) == check_date
    ).first()

    if existing and existing.status == 'PRESENT':
        return {
            'success': False,
            'status': 'DUPLICATE',
            'error_code': 'DUPLICATE',
            'attendance_type': 'MORNING_STUDENT',
            'message': f'Morning attendance already marked for today at {existing.scanned_at.strftime("%I:%M %p")}.'
        }

    try:
        rec = AttendanceRecord(
            session_id=None,
            student_id=student.id,
            attendance_type='MORNING_STUDENT',
            scanned_at=scanned_dt,
            student_lat=student_lat,
            student_lng=student_lng,
            status='PRESENT'
        )
        db.session.add(rec)
        db.session.commit()
        return {
            'success': True,
            'status': 'PRESENT',
            'attendance_type': 'MORNING_STUDENT',
            'message': 'Morning attendance marked successfully.'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'status': 'ERROR',
            'message': f'Database error: {str(e)}'
        }


def process_faculty_biometric_attendance(
    logged_in_user_id: int,
    scanned_barcode: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    target_datetime: Optional[datetime] = None,
    force_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handles Faculty Biometric / ID check-in (Morning arrival & Evening check-out).
    """
    faculty = Faculty.query.filter_by(user_id=logged_in_user_id).first()
    if not faculty:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'ROLE_DENIED',
            'message': "Access denied: Only faculty members can record faculty attendance."
        }

    target_faculty = identify_faculty_by_barcode(scanned_barcode)
    if not target_faculty or target_faculty.user_id != logged_in_user_id:
        return {
            'success': False,
            'status': 'REJECTED',
            'error_code': 'PROXY_REJECTED',
            'message': "You can only scan your own faculty ID badge. Proxy scans are prohibited."
        }

    ist_now = target_datetime or get_server_ist_datetime()
    att_date = ist_now.date()

    if force_type in ['FACULTY_MORNING', 'FACULTY_EVENING']:
        att_type = force_type
    else:
        att_type = 'FACULTY_MORNING' if ist_now.time() < time(13, 0) else 'FACULTY_EVENING'

    existing_entry = FacultyAttendance.query.filter_by(
        faculty_id=faculty.id,
        attendance_date=att_date,
        attendance_type=att_type
    ).first()

    if existing_entry and existing_entry.status == 'PRESENT':
        return {
            'success': False,
            'status': 'DUPLICATE',
            'error_code': 'DUPLICATE',
            'attendance_type': att_type,
            'message': f"{att_type} already recorded for today at {existing_entry.scanned_at.strftime('%I:%M %p')}."
        }

    try:
        rec = FacultyAttendance(
            faculty_id=faculty.id,
            attendance_date=att_date,
            attendance_type=att_type,
            scanned_at=ist_now,
            latitude=latitude,
            longitude=longitude,
            status='PRESENT'
        )
        db.session.add(rec)

        log = AuditLog(
            user_id=logged_in_user_id,
            action=f'{att_type}_RECORDED',
            details=f"Faculty {faculty.faculty_id} ({faculty.user.name}) recorded {att_type}"
        )
        db.session.add(log)
        db.session.commit()

        return {
            'success': True,
            'status': 'PRESENT',
            'attendance_type': att_type,
            'date': att_date.strftime('%d-%m-%Y'),
            'scanned_at': ist_now.strftime('%I:%M:%S %p'),
            'message': f"{att_type} recorded successfully."
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'status': 'ERROR',
            'message': f"Database error recording faculty attendance: {str(e)}"
        }

