"""
Unit and Integration Tests for HOD Timetable CRUD and Conflict Validation
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Timetable, Subject, Faculty, ClassRoom
from init_db import initialize_database
from services.timetable_service import (
    add_timetable_slot,
    update_timetable_slot,
    delete_timetable_slot,
    check_timetable_conflict
)

class TimetableCRUDTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def _login_hod(self):
        return self.client.post('/login', data={
            'role': 'HOD',
            'identifier': 'hod@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)

    def _login_student(self):
        return self.client.post('/login', data={
            'role': 'STUDENT',
            'identifier': 'AIML001',
            'password': 'Password123!'
        }, follow_redirects=True)

    def test_hod_can_view_timetable(self):
        """HOD can access the Timetable Master view with all slots."""
        self._login_hod()
        res = self.client.get('/hod/timetable')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Timetable Master Schedule', res.text)
        self.assertIn('FDS', res.text)
        self.assertIn('DSA', res.text)

    def test_add_and_delete_slot(self):
        """Test adding a new slot on Saturday Hour 4 (or modifying) and deleting it."""
        with self.app.app_context():
            cls_obj = ClassRoom.query.first()
            sub_obj = Subject.query.filter_by(short_name='DSA').first()
            fac_obj = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()

            # Add temporary slot
            slot, msg = add_timetable_slot(
                class_id=cls_obj.id,
                day_of_week='Saturday',
                hour_number=7,
                subject_id=sub_obj.id,
                faculty_id=fac_obj.id,
                academic_year='2026-2027'
            )
            # If already exists in seed, conflict might trigger, which is expected
            if not slot:
                self.assertIn('Conflict', msg)
            else:
                self.assertIsNotNone(slot)
                # Delete it
                success, del_msg = delete_timetable_slot(slot.id)
                self.assertTrue(success)

    def test_conflict_detection_faculty_double_booking(self):
        """Ensure system detects and rejects faculty double booking."""
        with self.app.app_context():
            # In seed data, Monday Hour 2 is DSA with Mr. Eshwar (FAC_AIML_002)
            fac_eshwar = Faculty.query.filter_by(faculty_id='FAC_AIML_002').first()
            cls_obj = ClassRoom.query.first()
            
            # Check conflict for Monday Hour 2 with Eshwar
            has_conflict, msg = check_timetable_conflict(
                day_of_week='Monday',
                hour_number=2,
                class_id=cls_obj.id,
                faculty_id=fac_eshwar.id
            )
            self.assertTrue(has_conflict)
            self.assertIn('Conflict', msg)

    def test_student_cannot_modify_timetable(self):
        """Ensure Student role is blocked from calling timetable modification routes."""
        self._login_student()

        # Try to post to /hod/timetable/add
        res_add = self.client.post('/hod/timetable/add', data={
            'class_id': 1,
            'day_of_week': 'Monday',
            'hour_number': 1,
            'subject_id': 1,
            'faculty_id': 1
        }, follow_redirects=True)
        self.assertIn('Access denied', res_add.text)

        # Try to post to /hod/timetable/delete/1
        res_del = self.client.post('/hod/timetable/delete/1', follow_redirects=True)
        self.assertIn('Access denied', res_del.text)

if __name__ == '__main__':
    unittest.main()
