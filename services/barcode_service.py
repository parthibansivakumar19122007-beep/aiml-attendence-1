from typing import Optional, Tuple, Dict, Any
from models import Student, Faculty, User

def identify_student_by_barcode(scanned_code: str) -> Optional[Student]:
    """
    Resolves a scanned QR/Barcode string or Student ID into a Student model record.
    Matches against student_id or barcode_value.
    """
    if not scanned_code or not str(scanned_code).strip():
        return None

    code = str(scanned_code).strip()
    return Student.query.filter_by(student_id=code).first()

def identify_faculty_by_barcode(scanned_code: str) -> Optional[Faculty]:
    """
    Resolves a scanned QR/Barcode string or Staff ID into a Faculty model record.
    Matches against faculty_id or barcode_value.
    """
    if not scanned_code or not str(scanned_code).strip():
        return None

    code = str(scanned_code).strip()
    return Faculty.query.filter_by(faculty_id=code).first()

def validate_student_id_card_ownership(
    logged_in_user_id: int, 
    scanned_code: str
) -> Tuple[bool, Optional[Student], str]:
    """
    Anti-Proxy Security Check:
    Verifies that the scanned ID badge genuinely belongs to the logged-in student user.
    """
    student = identify_student_by_barcode(scanned_code)
    if not student:
        return False, None, "Invalid ID card: Badge not recognized in department records."

    if student.user_id != logged_in_user_id:
        return False, student, "Attendance rejected: You can only scan your own official ID card badge. Proxy scans are prohibited."

    return True, student, "ID badge verified successfully."
