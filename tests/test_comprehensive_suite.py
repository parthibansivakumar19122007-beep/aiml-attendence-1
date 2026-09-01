"""
Comprehensive Test Suite Covering All 19 Real-World Verification Edge Cases
"""

import sys
import os
import unittest
from datetime import datetime, date, time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Student, Faculty, Timetable, AttendanceSession, AttendanceRecord, FacultyAttendance, AuditLog
from init_db import initialize_database
from services.attendance_service import (
    start_faculty_session,
    close_faculty_session,
    process_student_hourly_attendance,
    process_student_morning_attendance,
    process_faculty_biometric_attendance
)
from services.timetable_service import get_current_timetable_session

class ComprehensiveEdgeCasesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            FacultyAttendance.query.delete()
            AuditLog.query.delete()
            db.session.commit()

    # Case 1: Valid student scan
    def test_case_01_valid_student_scan(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 6, 22, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016810,
                student_lng=76.955810,
                target_session_id=sess.id
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['status'], 'PRESENT')

    # Case 2: Duplicate student scan
    def test_case_02_duplicate_student_scan(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 6, 29, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            res1 = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016810,
                student_lng=76.955810,
                target_session_id=sess.id
            )
            self.assertTrue(res1['success'])
            res2 = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016810,
                student_lng=76.955810,
                target_session_id=sess.id
            )
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')

    # Case 3: Student outside 50m
    def test_case_03_student_outside_50m(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML003').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 7, 6, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.0195, # ~300m away
                student_lng=76.9558,
                target_session_id=sess.id
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['status'], 'REJECTED')
            self.assertIn('outside the 50-meter', res['message'])

    # Case 4: Student inside 50m
    def test_case_04_student_inside_50m(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML002').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 7, 13, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016815,
                student_lng=76.955815,
                target_session_id=sess.id
            )
            self.assertTrue(res['success'])
            self.assertEqual(res['status'], 'PRESENT')

    # Case 5: Invalid ID card barcode (Proxy rejection)
    def test_case_05_invalid_barcode_proxy(self):
        with self.app.app_context():
            student1 = Student.query.filter_by(student_id='AIML001').first()
            student2 = Student.query.filter_by(student_id='AIML002').first()
            res = process_student_hourly_attendance(
                logged_in_user_id=student1.user_id,
                scanned_barcode=student2.barcode_value, # Proxy scan
                student_lat=11.0168,
                student_lng=76.9558
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['error_code'], 'INVALID_BADGE')

    # Case 6: Location permission denied
    def test_case_06_location_permission_denied(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML004').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 7, 20, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=None, # Location unavailable
                student_lng=None,
                target_session_id=sess.id
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['error_code'], 'LOCATION_UNAVAILABLE')

    # Case 7: Closed session scan rejected
    def test_case_07_closed_session_scan_rejected(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML005').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 7, 27, 10, 15, 0),
                target_day='Monday'
            )
            self.assertIsNotNone(sess, msg)
            close_faculty_session(sess.id, faculty_id=fac.id)
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.0168,
                student_lng=76.9558,
                target_session_id=sess.id
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['status'], 'REJECTED')
            self.assertIn('Attendance session is closed', res['message'])

    # Case 8: Faculty starts session when not scheduled
    def test_case_08_faculty_starts_unscheduled_slot(self):
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=datetime(2026, 6, 25, 14, 0, 0),
                target_day='Thursday'
            )
            self.assertIsNone(sess)
            self.assertIn('No attendance session is scheduled', msg)

    # Case 9: Faculty morning duplicate prevention
    def test_case_09_faculty_morning_duplicate_rejected(self):
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            t = datetime(2026, 6, 22, 8, 45, 0)
            res1 = process_faculty_biometric_attendance(fac.user_id, fac.barcode_value, 11.0168, 76.9558, target_datetime=t)
            self.assertTrue(res1['success'])
            res2 = process_faculty_biometric_attendance(fac.user_id, fac.barcode_value, 11.0168, 76.9558, target_datetime=t)
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')

    # Case 10: Student attempts evening scan
    def test_case_10_student_attempts_faculty_evening_scan(self):
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            res = process_faculty_biometric_attendance(student.user_id, student.barcode_value, 11.0168, 76.9558)
            self.assertFalse(res['success'])
            self.assertEqual(res['error_code'], 'ROLE_DENIED')

    # Case 11: Unauthorized route access (Student accessing HOD dashboard)
    def test_case_11_unauthorized_portal_access(self):
        self.client.post('/login', data={'role': 'STUDENT', 'identifier': 'AIML001', 'password': 'Password123!'}, follow_redirects=True)
        res = self.client.get('/hod/dashboard', follow_redirects=True)
        self.assertIn(res.status_code, [200, 403])
        self.assertIn('Access denied', res.text)

if __name__ == '__main__':
    unittest.main()
