"""
Unit and Integration Tests for Faculty Attendance Session Lifecycle (Start, End, GPS, Live Feed)
"""

import sys
import os
import unittest
from datetime import datetime, date, time, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Faculty, Timetable, AttendanceSession, AttendanceRecord, Student
from init_db import initialize_database
from services.attendance_service import (
    start_faculty_session,
    close_faculty_session,
    get_session_live_feed,
    auto_expire_stale_sessions
)

class FacultySessionLifecycleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            AttendanceRecord.query.delete()
            AttendanceSession.query.delete()
            db.session.commit()

    def _login_faculty(self, email='eswar@example.com'):
        return self.client.post('/login', data={
            'role': 'FACULTY',
            'identifier': email,
            'password': 'Password123!'
        }, follow_redirects=True)

    def test_start_and_end_session_with_gps(self):
        """Test starting attendance session with GPS and ending it."""
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first() # Mr. Eshwar Vadivel
            
            # Start session simulating Monday Hour 2 (DSA)
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            sess, msg = start_faculty_session(
                faculty_id=fac.id,
                latitude=11.016844,
                longitude=76.955832,
                security_radius_m=50.0,
                target_datetime=monday_1015,
                target_day='Monday'
            )
            self.assertIsNotNone(sess)
            self.assertEqual(sess.status, 'OPEN')
            self.assertAlmostEqual(float(sess.faculty_lat), 11.016844, places=5)
            self.assertAlmostEqual(float(sess.faculty_lng), 76.955832, places=5)
            self.assertEqual(float(sess.security_radius_m), 50.0)

            # Test live feed
            feed = get_session_live_feed(sess.id, faculty_id=fac.id)
            self.assertEqual(feed['status'], 'OPEN')
            self.assertEqual(feed['present_count'], 0)

            # End session
            success, end_msg = close_faculty_session(sess.id, faculty_id=fac.id)
            self.assertTrue(success)
            
            updated_sess = db.session.get(AttendanceSession, sess.id)
            self.assertEqual(updated_sess.status, 'CLOSED')
            self.assertIsNotNone(updated_sess.closed_at)

    def test_prevent_unauthorized_faculty_closing_session(self):
        """Ensure faculty A cannot close a session opened by faculty B."""
        with self.app.app_context():
            fac_eshwar = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            fac_shobana = Faculty.query.filter_by(faculty_id='FAC_AIML_001').first()

            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)
            sess, _ = start_faculty_session(
                faculty_id=fac_eshwar.id,
                latitude=11.0168,
                longitude=76.9558,
                target_datetime=monday_1015,
                target_day='Monday'
            )
            self.assertIsNotNone(sess)

            # Shobana attempts to close Eshwar's session
            success, msg = close_faculty_session(sess.id, faculty_id=fac_shobana.id)
            self.assertFalse(success)
            self.assertIn('Unauthorized', msg)

            # Clean up
            close_faculty_session(sess.id, faculty_id=fac_eshwar.id)

    def test_flask_route_session_start_and_end(self):
        """Test the Flask POST routes for session start and end."""
        self._login_faculty('eswar@example.com')

        # Start session via POST
        res_start = self.client.post('/faculty/session/start', data={
            'latitude': '11.0168',
            'longitude': '76.9558',
            'sim_time': '10:15',
            'sim_day': 'Monday'
        }, follow_redirects=True)

        self.assertEqual(res_start.status_code, 200)

        # Get active session ID from DB
        with self.app.app_context():
            fac = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            active_sess = AttendanceSession.query.filter_by(faculty_id=fac.id, status='OPEN').first()
            if active_sess:
                # End session via POST
                res_end = self.client.post(f'/faculty/session/end/{active_sess.id}', follow_redirects=True)
                self.assertEqual(res_end.status_code, 200)
                self.assertIn('closed successfully', res_end.text)

if __name__ == '__main__':
    unittest.main()
