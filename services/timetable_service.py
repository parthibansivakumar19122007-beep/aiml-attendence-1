from datetime import time, datetime, date
from typing import Optional, List, Tuple, Dict, Any
import pytz
from flask import current_app
from models import db, Timetable, ClassRoom, Subject, Faculty, AuditLog, AttendanceSession, Student

DEFAULT_HOUR_TIMINGS = {
    1: (time(9, 10), time(10, 0)),    # 09:10 AM – 10:00 AM
    2: (time(10, 0), time(10, 50)),   # 10:00 AM – 10:50 AM
    3: (time(11, 10), time(12, 0)),   # 11:10 AM – 12:00 PM
    4: (time(12, 0), time(12, 50)),   # 12:00 PM – 12:50 PM
    5: (time(13, 40), time(14, 30)),  # 01:40 PM – 02:30 PM
    6: (time(14, 30), time(15, 20)),  # 02:30 PM – 03:20 PM
    7: (time(15, 20), time(16, 10)),  # 03:20 PM – 04:10 PM
}

def get_server_ist_datetime() -> datetime:
    """Returns current server datetime strictly in Asia/Kolkata timezone."""
    tz_name = current_app.config.get('TIMEZONE', 'Asia/Kolkata') if current_app else 'Asia/Kolkata'
    tz = pytz.timezone(tz_name)
    return datetime.now(tz)

def get_default_times_for_hour(hour_number: int) -> Tuple[time, time]:
    return DEFAULT_HOUR_TIMINGS.get(hour_number, (time(9, 0), time(10, 0)))

def parse_time_str(time_val: Any) -> Optional[time]:
    if isinstance(time_val, time):
        return time_val
    if not time_val:
        return None
    time_str = str(time_val).strip()
    for fmt in ('%H:%M:%S', '%H:%M', '%I:%M %p', '%I:%M%p'):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None

def check_timetable_conflict(
    day_of_week: str,
    hour_number: int,
    class_id: int,
    faculty_id: int,
    academic_year: str = '2026-2027',
    exclude_slot_id: Optional[int] = None
) -> Tuple[bool, str]:
    faculty_conflict_query = Timetable.query.filter(
        Timetable.day_of_week == day_of_week,
        Timetable.hour_number == hour_number,
        Timetable.faculty_id == faculty_id,
        Timetable.academic_year == academic_year,
        Timetable.is_active == True
    )
    if exclude_slot_id:
        faculty_conflict_query = faculty_conflict_query.filter(Timetable.id != exclude_slot_id)
    
    faculty_conflict = faculty_conflict_query.first()
    if faculty_conflict:
        fac_name = faculty_conflict.faculty.user.name if (faculty_conflict.faculty and faculty_conflict.faculty.user) else "Faculty"
        return True, f"Conflict: {fac_name} is already assigned to {faculty_conflict.classroom.class_name} on {day_of_week}, Hour {hour_number}."

    class_conflict_query = Timetable.query.filter(
        Timetable.day_of_week == day_of_week,
        Timetable.hour_number == hour_number,
        Timetable.class_id == class_id,
        Timetable.academic_year == academic_year,
        Timetable.is_active == True
    )
    if exclude_slot_id:
        class_conflict_query = class_conflict_query.filter(Timetable.id != exclude_slot_id)
    
    class_conflict = class_conflict_query.first()
    if class_conflict:
        sub_name = class_conflict.subject.short_name if class_conflict.subject else "Subject"
        return True, f"Conflict: This class already has '{sub_name}' scheduled on {day_of_week}, Hour {hour_number}."

    return False, ""

def add_timetable_slot(
    class_id: int,
    day_of_week: str,
    hour_number: int,
    subject_id: int,
    faculty_id: int,
    academic_year: str = '2026-2027',
    start_time_val: Optional[str] = None,
    end_time_val: Optional[str] = None,
    is_active: bool = True,
    user_id: Optional[int] = None
) -> Tuple[Optional[Timetable], str]:
    if hour_number < 1 or hour_number > 7:
        return None, "Invalid hour number. Must be between 1 and 7."

    start_t = parse_time_str(start_time_val)
    end_t = parse_time_str(end_time_val)
    def_start, def_end = get_default_times_for_hour(hour_number)
    start_t = start_t or def_start
    end_t = end_t or def_end

    has_conflict, msg = check_timetable_conflict(
        day_of_week=day_of_week,
        hour_number=hour_number,
        class_id=class_id,
        faculty_id=faculty_id,
        academic_year=academic_year
    )
    if has_conflict:
        return None, msg

    try:
        slot = Timetable(
            academic_year=academic_year,
            class_id=class_id,
            day_of_week=day_of_week,
            hour_number=hour_number,
            subject_id=subject_id,
            faculty_id=faculty_id,
            start_time=start_t,
            end_time=end_t,
            is_active=is_active
        )
        db.session.add(slot)
        db.session.flush()

        if user_id:
            log = AuditLog(
                user_id=user_id,
                action='HOD_ADDED_TIMETABLE',
                details=f"Added timetable slot ID:{slot.id} ({day_of_week} H{hour_number})"
            )
            db.session.add(log)

        db.session.commit()
        return slot, "Timetable slot added successfully."
    except Exception as e:
        db.session.rollback()
        return None, f"Database error: {str(e)}"

def update_timetable_slot(
    slot_id: int,
    class_id: int,
    day_of_week: str,
    hour_number: int,
    subject_id: int,
    faculty_id: int,
    academic_year: str = '2026-2027',
    start_time_val: Optional[str] = None,
    end_time_val: Optional[str] = None,
    is_active: bool = True,
    user_id: Optional[int] = None
) -> Tuple[Optional[Timetable], str]:
    slot = db.session.get(Timetable, slot_id)
    if not slot:
        return None, "Timetable entry not found."

    start_t = parse_time_str(start_time_val) or slot.start_time
    end_t = parse_time_str(end_time_val) or slot.end_time

    has_conflict, msg = check_timetable_conflict(
        day_of_week=day_of_week,
        hour_number=hour_number,
        class_id=class_id,
        faculty_id=faculty_id,
        academic_year=academic_year,
        exclude_slot_id=slot_id
    )
    if has_conflict:
        return None, msg

    try:
        slot.class_id = class_id
        slot.day_of_week = day_of_week
        slot.hour_number = hour_number
        slot.subject_id = subject_id
        slot.faculty_id = faculty_id
        slot.academic_year = academic_year
        slot.start_time = start_t
        slot.end_time = end_t
        slot.is_active = is_active

        if user_id:
            log = AuditLog(
                user_id=user_id,
                action='HOD_UPDATED_TIMETABLE',
                details=f"Updated timetable slot ID:{slot.id} ({day_of_week} H{hour_number})"
            )
            db.session.add(log)

        db.session.commit()
        return slot, "Timetable slot updated successfully."
    except Exception as e:
        db.session.rollback()
        return None, f"Database error: {str(e)}"

def delete_timetable_slot(slot_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
    slot = db.session.get(Timetable, slot_id)
    if not slot:
        return False, "Timetable slot not found."

    active_sessions_count = AttendanceSession.query.filter_by(timetable_id=slot_id, status='OPEN').count()
    if active_sessions_count > 0:
        return False, "Cannot delete slot: There is currently an OPEN attendance session for this class slot."

    try:
        desc = f"{slot.day_of_week} Hour {slot.hour_number} ({slot.subject.short_name if slot.subject else ''})"
        db.session.delete(slot)

        if user_id:
            log = AuditLog(
                user_id=user_id,
                action='HOD_DELETED_TIMETABLE',
                details=f"Deleted timetable slot ID:{slot_id} ({desc})"
            )
            db.session.add(log)

        db.session.commit()
        return True, f"Timetable slot ({desc}) deleted successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Error deleting timetable slot: {str(e)}"

def toggle_timetable_slot_status(slot_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
    slot = db.session.get(Timetable, slot_id)
    if not slot:
        return False, "Timetable slot not found."

    try:
        slot.is_active = not slot.is_active
        new_status = "Active" if slot.is_active else "Inactive"

        if user_id:
            log = AuditLog(
                user_id=user_id,
                action='HOD_TOGGLED_TIMETABLE_STATUS',
                details=f"Toggled slot ID:{slot_id} to {new_status}"
            )
            db.session.add(log)

        db.session.commit()
        return True, f"Timetable slot marked as {new_status}."
    except Exception as e:
        db.session.rollback()
        return False, f"Error updating status: {str(e)}"


# ============================================================================
# STAGE 4: AUTOMATIC CURRENT SESSION DETECTION ENGINE
# ============================================================================

def get_current_timetable_session(
    faculty_id: int, 
    target_datetime: Optional[datetime] = None,
    target_day: Optional[str] = None
) -> Dict[str, Any]:
    """
    Automatically detects the current timetable entry for a logged-in faculty member.
    """
    current_dt = target_datetime or get_server_ist_datetime()
    current_date = current_dt.date()
    current_day = target_day if target_day else current_dt.strftime('%A')
    current_time_obj = current_dt.time()

    # Sunday check (College working days: Mon - Sat)
    if current_day == 'Sunday':
        return {
            'is_scheduled': False,
            'message': 'Sunday is an institutional holiday. No attendance sessions scheduled.',
            'server_time': current_dt.strftime('%I:%M %p'),
            'server_date': current_date.strftime('%d-%m-%Y'),
            'day_of_week': current_day,
            'slot': None,
            'session': None
        }

    # Query all active timetable slots for this faculty today
    slots_today = Timetable.query.filter_by(
        faculty_id=faculty_id,
        day_of_week=current_day,
        is_active=True
    ).order_by(Timetable.hour_number.asc()).all()

    if not slots_today:
        return {
            'is_scheduled': False,
            'message': f"You have no classes scheduled on {current_day}.",
            'server_time': current_dt.strftime('%I:%M %p'),
            'server_date': current_date.strftime('%d-%m-%Y'),
            'day_of_week': current_day,
            'slot': None,
            'session': None,
            'today_slots_count': 0
        }

    # Find slot matching the current hour window
    matched_slot = None
    for slot in slots_today:
        if slot.start_time <= current_time_obj <= slot.end_time:
            matched_slot = slot
            break

    if not matched_slot:
        return {
            'is_scheduled': False,
            'message': 'No attendance session is scheduled for you at this time.',
            'server_time': current_dt.strftime('%I:%M %p'),
            'server_date': current_date.strftime('%d-%m-%Y'),
            'day_of_week': current_day,
            'slot': None,
            'session': None,
            'today_slots_count': len(slots_today)
        }

    # Check for existing attendance session for this slot today
    session_record = AttendanceSession.query.filter_by(
        timetable_id=matched_slot.id,
        date=current_date
    ).first()

    return {
        'is_scheduled': True,
        'message': f"Scheduled class detected: Hour {matched_slot.hour_number} - {matched_slot.subject.short_name}",
        'server_time': current_dt.strftime('%I:%M %p'),
        'server_date': current_date.strftime('%d-%m-%Y'),
        'day_of_week': current_day,
        'slot': matched_slot,
        'session': session_record,
        'session_status': session_record.status if session_record else 'NOT_STARTED'
    }

def get_current_class_session_for_student(
    class_id: int,
    target_datetime: Optional[datetime] = None,
    target_day: Optional[str] = None
) -> Dict[str, Any]:
    """
    Identifies the active class timetable slot and open attendance session for students.
    """
    current_dt = target_datetime or get_server_ist_datetime()
    current_date = current_dt.date()
    current_day = target_day if target_day else current_dt.strftime('%A')
    current_time_obj = current_dt.time()

    if current_day == 'Sunday':
        return {
            'has_class': False,
            'has_open_session': False,
            'message': 'No classes scheduled on Sunday.',
            'slot': None,
            'session': None
        }

    active_slot = Timetable.query.filter(
        Timetable.class_id == class_id,
        Timetable.day_of_week == current_day,
        Timetable.is_active == True,
        Timetable.start_time <= current_time_obj,
        Timetable.end_time >= current_time_obj
    ).first()

    if not active_slot:
        return {
            'has_class': False,
            'has_open_session': False,
            'message': 'No scheduled class for your section at this time.',
            'slot': None,
            'session': None
        }

    active_session = AttendanceSession.query.filter_by(
        timetable_id=active_slot.id,
        date=current_date,
        status='OPEN'
    ).first()

    return {
        'has_class': True,
        'has_open_session': bool(active_session),
        'message': f"Active class: Hour {active_slot.hour_number} - {active_slot.subject.short_name}",
        'slot': active_slot,
        'session': active_session
    }
