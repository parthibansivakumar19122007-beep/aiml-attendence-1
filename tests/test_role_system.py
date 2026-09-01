"""
Comprehensive 10-Point Role-Based Access Control Test Suite
Validates all requirements from the prompt specification.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from models import db, User, Student, Faculty

def run_tests():
    app = create_app()
    client = app.test_client()

    print("=" * 60)
    print("STARTING 10-POINT RBAC VERIFICATION SUITE")
    print("=" * 60)

    # ---------------------------------------------------------
    # TEST 1: Student login -> Student dashboard -> Cannot access others
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 1] Student login -> Dashboard -> Cannot access others...")
    res = client.post('/login', data={'username': 'student01', 'password': 'Password123!'}, follow_redirects=False)
    assert res.status_code == 302 and '/student/dashboard' in res.headers['Location'], f"Failed: {res.status_code}, {res.headers}"
    
    # Verify access to student dashboard
    res_dash = client.get('/student/dashboard')
    assert res_dash.status_code == 200, f"Student dashboard failed with {res_dash.status_code}"
    
    # Verify rejection on other portals (returns 403)
    res_fac = client.get('/faculty/dashboard')
    assert res_fac.status_code == 403, f"Expected 403 on faculty dashboard for student, got {res_fac.status_code}"
    res_hod = client.get('/hod/dashboard')
    assert res_hod.status_code == 403, f"Expected 403 on hod dashboard for student, got {res_hod.status_code}"
    res_adm = client.get('/admin/dashboard')
    assert res_adm.status_code == 403, f"Expected 403 on admin dashboard for student, got {res_adm.status_code}"
    print("[PASS] TEST 1: Student login routed to /student/dashboard; Faculty/HOD/Admin routes returned 403 Forbidden.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 2: Faculty login -> Faculty dashboard -> Cannot access others
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 2] Faculty login -> Dashboard -> Cannot access others...")
    res = client.post('/login', data={'username': 'faculty01', 'password': 'Password123!'}, follow_redirects=False)
    assert res.status_code == 302 and '/faculty/dashboard' in res.headers['Location'], f"Failed: {res.status_code}, {res.headers}"

    res_dash = client.get('/faculty/dashboard')
    assert res_dash.status_code == 200, f"Faculty dashboard failed with {res_dash.status_code}"

    res_st = client.get('/student/dashboard')
    assert res_st.status_code == 403, f"Expected 403 on student dashboard for faculty, got {res_st.status_code}"
    res_hod = client.get('/hod/dashboard')
    assert res_hod.status_code == 403, f"Expected 403 on hod dashboard for faculty, got {res_hod.status_code}"
    res_adm = client.get('/admin/dashboard')
    assert res_adm.status_code == 403, f"Expected 403 on admin dashboard for faculty, got {res_adm.status_code}"
    print("[PASS] TEST 2 PASSED: Faculty login routed to /faculty/dashboard; Student/HOD/Admin routes returned 403 Forbidden.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 3: HOD login -> HOD dashboard -> Cannot access others
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 3] HOD login -> Dashboard -> Cannot access others...")
    res = client.post('/login', data={'username': 'hod01', 'password': 'Password123!'}, follow_redirects=False)
    assert res.status_code == 302 and '/hod/dashboard' in res.headers['Location'], f"Failed: {res.status_code}, {res.headers}"

    res_dash = client.get('/hod/dashboard')
    assert res_dash.status_code == 200, f"HOD dashboard failed with {res_dash.status_code}"

    res_st = client.get('/student/dashboard')
    assert res_st.status_code == 403, f"Expected 403 on student dashboard for HOD, got {res_st.status_code}"
    res_fac = client.get('/faculty/dashboard')
    assert res_fac.status_code == 403, f"Expected 403 on faculty dashboard for HOD, got {res_fac.status_code}"
    res_adm = client.get('/admin/dashboard')
    assert res_adm.status_code == 403, f"Expected 403 on admin dashboard for HOD, got {res_adm.status_code}"
    print("[PASS] TEST 3 PASSED: HOD login routed to /hod/dashboard; Student/Faculty/Admin routes returned 403 Forbidden.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 4: Admin login -> Admin dashboard -> Can manage accounts
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 4] Admin login -> Dashboard -> Can manage accounts...")
    res = client.post('/login', data={'username': 'admin01', 'password': 'Password123!'}, follow_redirects=False)
    assert res.status_code == 302 and '/admin/dashboard' in res.headers['Location'], f"Failed: {res.status_code}, {res.headers}"

    res_dash = client.get('/admin/dashboard')
    assert res_dash.status_code == 200, f"Admin dashboard failed with {res_dash.status_code}"

    # Verify access to student, faculty, hod, user management
    assert client.get('/admin/students').status_code == 200, "Admin students failed"
    assert client.get('/admin/faculty').status_code == 200, "Admin faculty failed"
    assert client.get('/admin/hod').status_code == 200, "Admin HOD list failed"
    assert client.get('/admin/users').status_code == 200, "Admin users list failed"
    print("[PASS] TEST 4 PASSED: Admin login routed to /admin/dashboard; can access Students, Faculty, HOD, and Users management.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 5: Wrong password -> Rejected
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 5] Wrong password rejection...")
    res = client.post('/login', data={'username': 'student01', 'password': 'WrongPassword999'}, follow_redirects=True)
    assert b'Incorrect password' in res.data or b'Invalid credentials' in res.data, "Failed to display error on wrong password"
    assert res.status_code == 200
    print("[PASS] TEST 5 PASSED: Wrong password correctly rejected with flash alert.")

    # ---------------------------------------------------------
    # TEST 6: Unauthenticated user manually enters protected URL -> Redirect to login
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 6] Unauthenticated user enters protected URL...")
    client.get('/logout')
    res_prot = client.get('/admin/dashboard', follow_redirects=False)
    assert res_prot.status_code == 302 and '/login' in res_prot.headers['Location'], f"Expected redirect to login, got {res_prot.status_code}"
    res_prot2 = client.get('/student/dashboard', follow_redirects=False)
    assert res_prot2.status_code == 302 and '/login' in res_prot2.headers['Location'], f"Expected redirect to login, got {res_prot2.status_code}"
    print("[PASS] TEST 6 PASSED: Unauthenticated user redirected to /login.")

    # ---------------------------------------------------------
    # TEST 7: Student manually enters /admin/dashboard -> 403 Forbidden
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 7] Student manually enters /admin/dashboard...")
    client.post('/login', data={'username': 'student01', 'password': 'Password123!'})
    res_st_adm = client.get('/admin/dashboard')
    assert res_st_adm.status_code == 403, f"Expected 403, got {res_st_adm.status_code}"
    assert b'403 Forbidden' in res_st_adm.data or b'Restricted Access Area' in res_st_adm.data
    print("[PASS] TEST 7 PASSED: Student manually accessing /admin/dashboard received HTTP 403 Forbidden page.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 8: Faculty manually enters /admin/dashboard -> 403 Forbidden
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 8] Faculty manually enters /admin/dashboard...")
    client.post('/login', data={'username': 'faculty01', 'password': 'Password123!'})
    res_fac_adm = client.get('/admin/dashboard')
    assert res_fac_adm.status_code == 403, f"Expected 403, got {res_fac_adm.status_code}"
    assert b'403 Forbidden' in res_fac_adm.data or b'Restricted Access Area' in res_fac_adm.data
    print("[PASS] TEST 8 PASSED: Faculty manually accessing /admin/dashboard received HTTP 403 Forbidden page.")
    client.get('/logout')

    # ---------------------------------------------------------
    # TEST 9: Admin creates a Student -> Student logs in -> Student Portal automatically
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 9] Admin creates Student -> Student logs in -> Auto Student Portal...")
    client.post('/login', data={'username': 'admin01', 'password': 'Password123!'})
    
    # Unique test username and ID
    test_user = 'teststudent99'
    test_roll = 'AIML999'
    test_email = 'teststudent99@nit.edu'

    with app.app_context():
        # Cleanup if leftover from previous test
        u_old = User.query.filter_by(username=test_user).first()
        if u_old:
            Student.query.filter_by(user_id=u_old.id).delete()
            db.session.delete(u_old)
            db.session.commit()

    res_create = client.post('/admin/students/add', data={
        'name': 'Automated Test Student',
        'username': test_user,
        'student_id': test_roll,
        'email': test_email,
        'department': 'CSE-AIML',
        'password': 'StudentSecret123!',
        'class_id': 1,
        'section': 'A',
        'year': 1
    }, follow_redirects=False)
    assert res_create.status_code == 302 and '/admin/students' in res_create.headers['Location'], f"Failed creation: {res_create.status_code}"

    # Log out Admin
    client.get('/logout')

    # Log in as newly created student
    res_login_new = client.post('/login', data={'username': test_user, 'password': 'StudentSecret123!'}, follow_redirects=False)
    assert res_login_new.status_code == 302 and '/student/dashboard' in res_login_new.headers['Location'], f"New student failed to route to student dashboard: {res_login_new.headers}"
    res_new_dash = client.get('/student/dashboard')
    assert res_new_dash.status_code == 200
    print("[PASS] TEST 9 PASSED: Admin created new student account; student successfully logged in and auto-redirected to /student/dashboard.")

    # ---------------------------------------------------------
    # TEST 10: Admin deactivates a user -> That user cannot login
    # ---------------------------------------------------------
    print("\n[RUNNING TEST 10] Admin deactivates user -> User cannot login...")
    client.get('/logout')
    client.post('/login', data={'username': 'admin01', 'password': 'Password123!'})

    with app.app_context():
        u_deact = User.query.filter_by(username=test_user).first()
        assert u_deact is not None
        deact_id = u_deact.id

    # Toggle deactivate
    res_toggle = client.post(f'/admin/users/{deact_id}/toggle', follow_redirects=False)
    assert res_toggle.status_code == 302

    with app.app_context():
        u_check = User.query.get(deact_id)
        assert u_check.is_active is False, "User was not deactivated"

    # Logout Admin
    client.get('/logout')

    # Attempt login with deactivated user
    res_blocked = client.post('/login', data={'username': test_user, 'password': 'StudentSecret123!'}, follow_redirects=True)
    assert b'deactivated' in res_blocked.data.lower(), "Expected deactivation error message"
    print("[PASS] TEST 10 PASSED: Deactivated user is blocked from logging in with an appropriate notice.")

    # Cleanup test user
    with app.app_context():
        u_cleanup = User.query.get(deact_id)
        if u_cleanup:
            Student.query.filter_by(user_id=u_cleanup.id).delete()
            db.session.delete(u_cleanup)
            db.session.commit()

    print("\n" + "=" * 60)
    print("ALL 10 TEST CASES PASSED 100% SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
