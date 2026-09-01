"""
Unit and Integration Tests for HOD Analytics, CSV Export, Drill-down APIs, and iCampus Placeholder
"""

import sys
import os
import unittest
from datetime import datetime, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Student, Faculty, AttendanceSession, AttendanceRecord, Timetable
from init_db import initialize_database
from services.icampus_service import sync_attendance_to_icampus, get_icampus_status

class HODReportsAndICampusTestCase(unittest.TestCase):
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

    def _login_hod(self):
        return self.client.post('/login', data={
            'role': 'HOD',
            'identifier': 'hod@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)

    def test_hod_dashboard_access(self):
        """Test HOD Dashboard access and hour matrix."""
        self._login_hod()
        res = self.client.get('/hod/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn('AIML Department Overview', res.text)
        self.assertIn('Daily 7-Hour Academic Attendance Matrix', res.text)

    def test_hod_reports_page_and_csv_export(self):
        """Test HOD Reports view and official CSV download endpoint."""
        self._login_hod()
        
        # Reports HTML view
        res_reports = self.client.get('/hod/reports')
        self.assertEqual(res_reports.status_code, 200)
        self.assertIn('AIML Department Attendance Analytics', res_reports.text)
        self.assertIn('Subject-wise Attendance Distribution', res_reports.text)

        # CSV Export endpoint
        res_csv = self.client.get('/hod/reports/export-csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.mimetype, 'text/csv')
        self.assertIn('Student ID,Student Name,Email', res_csv.text)
        self.assertIn('AIML001', res_csv.text)

    def test_session_drilldown_api(self):
        """Test HOD drill-down API for individual student attendance records."""
        self._login_hod()
        with self.app.app_context():
            slot = Timetable.query.first()
            sess = AttendanceSession(
                timetable_id=slot.id,
                session_type='HOURLY',
                class_id=slot.class_id,
                faculty_id=slot.faculty_id,
                session_date=date.today(),
                opened_at=datetime.utcnow(),
                status='OPEN'
            )
            db.session.add(sess)
            db.session.commit()

            res = self.client.get(f'/hod/api/session-details/{sess.id}')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data['session_id'], sess.id)
            self.assertIn('records', data)

    def test_icampus_placeholder_disabled_by_default(self):
        """Verify iCampus service is securely disabled by default as specified."""
        status = get_icampus_status()
        self.assertFalse(status['enabled'])

        with self.app.app_context():
            student = Student.query.first()
            rec = AttendanceRecord(
                session_id=1,
                student_id=student.id,
                attendance_type='HOURLY_STUDENT',
                status='PRESENT'
            )
            sync_res = sync_attendance_to_icampus(rec)
            self.assertFalse(sync_res['synced'])
            self.assertEqual(sync_res['status'], 'DISABLED')
            self.assertIn('disabled by institution policy', sync_res['message'])

if __name__ == '__main__':
    unittest.main()
