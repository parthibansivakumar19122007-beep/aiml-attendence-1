"""
Unit and Integration Tests for Morning Student Attendance and Faculty Morning/Evening Check-in
"""

import sys
import os
import unittest
from datetime import datetime, date, time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Student, Faculty, AttendanceSession, AttendanceRecord, FacultyAttendance
from init_db import initialize_database
from services.attendance_service import (
    process_student_morning_attendance,
    process_faculty_biometric_attendance
)

class MorningAndFacultyAttendanceTestCase(unittest.TestCase):
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
            db.session.commit()

    def test_student_morning_attendance_workflow(self):
        """Test Student Morning Check-in and Duplicate Prevention."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            today_date = date(2026, 6, 22)

            # First scan: Marks PRESENT
            res1 = process_student_morning_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.0168,
                student_lng=76.9558,
                target_date=today_date
            )
            self.assertTrue(res1['success'])
            self.assertEqual(res1['status'], 'PRESENT')
            self.assertEqual(res1['attendance_type'], 'MORNING_STUDENT')

            # Verify in DB
            rec = AttendanceRecord.query.filter_by(student_id=student.id, attendance_type='MORNING_STUDENT').first()
            self.assertIsNotNone(rec)
            self.assertEqual(rec.status, 'PRESENT')

            # Second scan on same day: Rejected as DUPLICATE
            res2 = process_student_morning_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.0168,
                student_lng=76.9558,
                target_date=today_date
            )
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')
            self.assertIn('already marked', res2['message'])

    def test_faculty_morning_checkin(self):
        """Test Faculty Morning Check-in and Duplicate Prevention."""
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first() # Mr. Eshwar Vadivel
            morning_time = datetime(2026, 6, 22, 8, 45, 0) # 08:45 AM

            # 1. First morning scan: Marks PRESENT
            res1 = process_faculty_biometric_attendance(
                logged_in_user_id=fac.user_id,
                scanned_barcode=fac.barcode_value,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=morning_time
            )
            self.assertTrue(res1['success'])
            self.assertEqual(res1['status'], 'PRESENT')
            self.assertEqual(res1['attendance_type'], 'FACULTY_MORNING')

            # Verify in DB
            rec = FacultyAttendance.query.filter_by(
                faculty_id=fac.id, 
                attendance_date=morning_time.date(),
                attendance_type='FACULTY_MORNING'
            ).first()
            self.assertIsNotNone(rec)

            # 2. Second morning scan: Rejected as DUPLICATE
            res2 = process_faculty_biometric_attendance(
                logged_in_user_id=fac.user_id,
                scanned_barcode=fac.barcode_value,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=morning_time
            )
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')
            self.assertIn('already recorded', res2['message'])

    def test_faculty_evening_checkout(self):
        """Test Faculty Evening Check-out and Duplicate Prevention."""
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            evening_time = datetime(2026, 6, 22, 16, 30, 0) # 04:30 PM

            # 1. Evening scan: Marks PRESENT
            res1 = process_faculty_biometric_attendance(
                logged_in_user_id=fac.user_id,
                scanned_barcode=fac.barcode_value,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=evening_time
            )
            self.assertTrue(res1['success'])
            self.assertEqual(res1['status'], 'PRESENT')
            self.assertEqual(res1['attendance_type'], 'FACULTY_EVENING')

            # 2. Duplicate evening scan: Rejected
            res2 = process_faculty_biometric_attendance(
                logged_in_user_id=fac.user_id,
                scanned_barcode=fac.barcode_value,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=evening_time
            )
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')

    def test_student_cannot_mark_faculty_attendance(self):
        """Ensure a student user cannot call or record faculty biometric attendance."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()

            res = process_faculty_biometric_attendance(
                logged_in_user_id=student.user_id, # Logged in as student
                scanned_barcode=fac.barcode_value
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['error_code'], 'ROLE_DENIED')
            self.assertIn('Access denied', res['message'])

    def test_faculty_anti_proxy(self):
        """Ensure faculty member A cannot scan faculty member B's card."""
        with self.app.app_context():
            fac_eshwar = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            fac_shobana = Faculty.query.filter_by(faculty_id='FAC_AIML_001').first()

            res = process_faculty_biometric_attendance(
                logged_in_user_id=fac_eshwar.user_id,
                scanned_barcode=fac_shobana.barcode_value
            )
            self.assertFalse(res['success'])
            self.assertEqual(res['error_code'], 'PROXY_REJECTED')
            self.assertIn('own faculty ID badge', res['message'])

if __name__ == '__main__':
    unittest.main()
