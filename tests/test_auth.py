"""
Unit and Integration Tests for Authentication and Role-Based Access Control (RBAC)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['USE_SQLITE'] = '1'
from app import create_app
from models import db, User, Student, Faculty
from init_db import initialize_database

class AuthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def setUp(self):
        self.app = create_app()

    def test_student_login_with_id_and_email(self):
        """Test Student login using both Roll Number and Email."""
        client = self.app.test_client()
        # 1. Login with Roll Number (AIML001)
        res1 = client.post('/login', data={
            'role': 'STUDENT',
            'identifier': 'AIML001',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)
        self.assertIn('STUDENT PORTAL', res1.text)

        client.get('/logout', follow_redirects=True)

        # 2. Login with Email (student@example.com)
        res2 = client.post('/login', data={
            'role': 'STUDENT',
            'identifier': 'student@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertIn('STUDENT PORTAL', res2.text)
        client.get('/logout', follow_redirects=True)

    def test_faculty_login(self):
        """Test Faculty login and redirection to /faculty/dashboard."""
        client = self.app.test_client()
        res = client.post('/login', data={
            'role': 'FACULTY',
            'identifier': 'eswar@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('FACULTY PORTAL', res.text)
        client.get('/logout', follow_redirects=True)

    def test_hod_login(self):
        """Test HOD login and redirection to /hod/dashboard."""
        client = self.app.test_client()
        res = client.post('/login', data={
            'role': 'HOD',
            'identifier': 'hod@example.com',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('AIML Department Overview', res.text)
        client.get('/logout', follow_redirects=True)

    def test_invalid_credentials(self):
        """Test login rejection for wrong passwords."""
        client = self.app.test_client()
        res = client.post('/login', data={
            'role': 'STUDENT',
            'identifier': 'AIML001',
            'password': 'WrongPassword999!'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Invalid credentials', res.text)
        client.get('/logout', follow_redirects=True)

    def test_unauthenticated_redirection(self):
        """Test protected routes redirect unauthenticated users to login page."""
        client = self.app.test_client()
        res = client.get('/student/dashboard', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Please log in to access this page', res.text)

    def test_cross_role_access_restriction(self):
        """Test that a Student cannot access the Faculty or HOD dashboards."""
        client = self.app.test_client()
        client.post('/login', data={
            'role': 'STUDENT',
            'identifier': 'AIML001',
            'password': 'Password123!'
        }, follow_redirects=True)

        res_fac = client.get('/faculty/dashboard', follow_redirects=True)
        self.assertIn(res_fac.status_code, [200, 403])
        self.assertIn('Access denied', res_fac.text)

        res_hod = client.get('/hod/dashboard', follow_redirects=True)
        self.assertIn(res_hod.status_code, [200, 403])
        self.assertIn('Access denied', res_hod.text)
        client.get('/logout', follow_redirects=True)

if __name__ == '__main__':
    unittest.main()
