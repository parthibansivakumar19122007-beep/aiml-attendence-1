"""
Unit and Integration Tests for Student Barcode/QR Scanning and 50m Geofence Validation
"""

import sys
import os
import unittest
from datetime import datetime, date, time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Student, Faculty, Timetable, AttendanceSession, AttendanceRecord, ClassRoom
from init_db import initialize_database
from services.attendance_service import (
    start_faculty_session,
    close_faculty_session,
    process_student_hourly_attendance
)
from services.location_service import haversine_distance_meters, verify_geofence_proximity

class StudentScanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            # Clean attendance records and sessions before each test
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            db.session.commit()

    def test_haversine_distance_calculation(self):
        """Test Haversine distance formula accuracy."""
        # Known points (approx 20 meters apart)
        lat1, lon1 = 11.016800, 76.955800
        lat2, lon2 = 11.016950, 76.955800
        dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
        self.assertTrue(15 < dist < 25)

        # Test points > 100 meters apart
        lat3, lon3 = 11.018000, 76.955800
        dist_far = haversine_distance_meters(lat1, lon1, lat3, lon3)
        self.assertTrue(dist_far > 100)

    def test_valid_student_scan_inside_50m(self):
        """Test that a valid student within 50m marks PRESENT."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            # Start faculty session at reference point
            fac_lat, fac_lng = 11.016844, 76.955832
            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=fac_lat,
                longitude=fac_lng,
                target_datetime=monday_1015,
                target_day='Monday'
            )
            self.assertIsNotNone(sess, f"Session could not be started: {msg}")

            # Student scans 10 meters away from faculty
            stu_lat, stu_lng = 11.016900, 76.955832
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=stu_lat,
                student_lng=stu_lng,
                target_session_id=sess.id
            )

            self.assertTrue(res['success'], f"Scan failed: {res.get('message')}")
            self.assertEqual(res['status'], 'PRESENT')
            self.assertIn('PRESENT ✓', res['message'])
            self.assertTrue(res['distance_m'] <= 50.0)

            # Verify in DB
            rec = AttendanceRecord.query.filter_by(session_id=sess.id, student_id=student.id).first()
            self.assertIsNotNone(rec)
            self.assertEqual(rec.status, 'PRESENT')

            # Clean up session
            close_faculty_session(sess.id, faculty_id=fac.id)

    def test_duplicate_scan_rejected(self):
        """Test that scanning twice in the same session is rejected as DUPLICATE."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            sess, _ = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.016844,
                longitude=76.955832,
                target_datetime=monday_1015,
                target_day='Monday'
            )

            # First scan -> PRESENT
            res1 = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016850,
                student_lng=76.955832,
                target_session_id=sess.id
            )
            self.assertTrue(res1['success'])

            # Second scan -> DUPLICATE
            res2 = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=11.016850,
                student_lng=76.955832,
                target_session_id=sess.id
            )
            self.assertFalse(res2['success'])
            self.assertEqual(res2['status'], 'DUPLICATE')
            self.assertIn('already marked', res2['message'])

            close_faculty_session(sess.id, faculty_id=fac.id)

    def test_outside_50m_geofence_rejected(self):
        """Test that a student outside the 50m radius is rejected."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML002').first() # Aarav
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            sess, _ = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.016844,
                longitude=76.955832,
                target_datetime=monday_1015,
                target_day='Monday'
            )

            # Student is located ~300 meters away
            far_lat, far_lng = 11.019800, 76.955832
            res = process_student_hourly_attendance(
                logged_in_user_id=student.user_id,
                scanned_barcode=student.barcode_value,
                student_lat=far_lat,
                student_lng=far_lng,
                target_session_id=sess.id
            )

            self.assertFalse(res['success'])
            self.assertEqual(res['status'], 'REJECTED')
            self.assertIn('outside the 50-meter attendance area', res['message'])
            self.assertTrue(res['distance_m'] > 50.0)

            close_faculty_session(sess.id, faculty_id=fac.id)

    def test_anti_proxy_badge_check(self):
        """Ensure a logged-in student cannot scan another student's ID card."""
        with self.app.app_context():
            student_parthiban = Student.query.filter_by(student_id='AIML001').first()
            student_aarav = Student.query.filter_by(student_id='AIML002').first()

            # Parthiban is logged in, but scans Aarav's barcode
            res = process_student_hourly_attendance(
                logged_in_user_id=student_parthiban.user_id,
                scanned_barcode=student_aarav.barcode_value,
                student_lat=11.0168,
                student_lng=76.9558
            )

            self.assertFalse(res['success'])
            self.assertEqual(res['status'], 'REJECTED')
            self.assertIn('Proxy scans are prohibited', res['message'])

    def test_scan_when_session_closed_rejected(self):
        """Ensure scanning after session is closed returns session closed error."""
        with self.app.app_context():
            student = Student.query.filter_by(student_id='AIML001').first()
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            sess, _ = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=monday_1015,
                target_day='Monday'
            )
            # Close session immediately
            close_faculty_session(sess.id, faculty_id=fac.id)

            # Student tries to scan
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

if __name__ == '__main__':
    unittest.main()
