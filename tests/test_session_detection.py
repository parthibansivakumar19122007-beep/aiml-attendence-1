"""
Unit and Integration Tests for Automatic Current-Session Detection Engine
"""

import sys
import os
import unittest
from datetime import datetime, date, time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Timetable, Subject, Faculty, ClassRoom
from init_db import initialize_database
from services.timetable_service import (
    get_current_timetable_session,
    get_current_class_session_for_student
)

class SessionDetectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_monday_hour2_dsa_detection_for_eshwar(self):
        """
        Monday at 10:15 AM:
        Mr. M. Eshwar Vadivel (FAC_AIML_002) is scheduled for Hour 2 (DSA, 10:00 - 10:50 AM).
        """
        with self.app.app_context():
            fac_eshwar = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            self.assertIsNotNone(fac_eshwar)

            # Construct mock datetime: Monday, 10:15 AM
            # 2026-06-22 was a Monday
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)
            
            res = get_current_timetable_session(fac_eshwar.id, target_datetime=monday_1015)
            self.assertTrue(res['is_scheduled'])
            self.assertIsNotNone(res['slot'])
            self.assertEqual(res['slot'].hour_number, 2)
            self.assertEqual(res['slot'].subject.short_name, 'DSA')
            self.assertEqual(res['day_of_week'], 'Monday')

    def test_monday_hour2_detection_for_other_faculty_returns_not_scheduled(self):
        """
        Monday at 10:15 AM:
        Dr. A. Shobana is NOT scheduled at Hour 2 (her class is Hour 3 at 11:10 AM).
        """
        with self.app.app_context():
            fac_shobana = Faculty.query.filter_by(faculty_id='FAC_AIML_001').first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)
            
            res = get_current_timetable_session(fac_shobana.id, target_datetime=monday_1015)
            self.assertFalse(res['is_scheduled'])
            self.assertIsNone(res['slot'])
            self.assertIn('No attendance session is scheduled for you', res['message'])

    def test_monday_hour3_dm_detection_for_shobana(self):
        """
        Monday at 11:30 AM:
        Dr. A. Shobana (FAC_AIML_001) is scheduled for Hour 3 (DM, 11:10 - 12:00 PM).
        """
        with self.app.app_context():
            fac_shobana = Faculty.query.filter_by(faculty_id='FAC_AIML_001').first()
            monday_1130 = datetime(2026, 6, 22, 11, 30, 0)
            
            res = get_current_timetable_session(fac_shobana.id, target_datetime=monday_1130)
            self.assertTrue(res['is_scheduled'])
            self.assertIsNotNone(res['slot'])
            self.assertEqual(res['slot'].hour_number, 3)
            self.assertEqual(res['slot'].subject.short_name, 'DM')

    def test_sunday_holiday_detection(self):
        """
        Sunday anytime returns institutional holiday notice.
        """
        with self.app.app_context():
            fac_eshwar = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            # 2026-06-21 was a Sunday
            sunday_dt = datetime(2026, 6, 21, 10, 15, 0)
            
            res = get_current_timetable_session(fac_eshwar.id, target_datetime=sunday_dt)
            self.assertFalse(res['is_scheduled'])
            self.assertIn('holiday', res['message'].lower())

    def test_student_class_detection(self):
        """
        Student in I B.E II AIML on Monday at 10:15 AM detects Hour 2 (DSA).
        """
        with self.app.app_context():
            cls_obj = ClassRoom.query.first()
            monday_1015 = datetime(2026, 6, 22, 10, 15, 0)

            res = get_current_class_session_for_student(cls_obj.id, target_datetime=monday_1015)
            self.assertTrue(res['has_class'])
            self.assertEqual(res['slot'].hour_number, 2)
            self.assertEqual(res['slot'].subject.short_name, 'DSA')

    def test_api_current_session_endpoint(self):
        """Test the live JSON API endpoint for faculty session detection."""
        # Login as faculty Mr. Eshwar
        self.client.post('/login', data={
            'role': 'FACULTY',
            'identifier': 'eswar@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)

        res = self.client.get('/faculty/api/current-session?sim_time=10:15&sim_day=Monday')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_scheduled'])
        self.assertEqual(data['slot']['subject_short'], 'DSA')
        self.assertEqual(data['slot']['hour_number'], 2)

if __name__ == '__main__':
    unittest.main()
