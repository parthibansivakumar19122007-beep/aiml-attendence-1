from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Student, Faculty, AuditLog
from services.auth_service import login_user_session, logout_user_session

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Root redirect based on user authentication status."""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'STUDENT':
            return redirect(url_for('student.dashboard'))
        elif role == 'FACULTY':
            return redirect(url_for('faculty.dashboard'))
        elif role == 'HOD':
            return redirect(url_for('hod.dashboard'))
        elif role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login_view', role='student'))

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/login/<role_param>', methods=['GET', 'POST'])
def login_view(role_param=None):
    """Unified 4-Role Login View (STUDENT, FACULTY, HOD, ADMIN)."""
    target_role = (role_param or request.args.get('role', 'student')).upper()
    if target_role not in ['STUDENT', 'FACULTY', 'HOD', 'ADMIN']:
        target_role = 'STUDENT'

    # If already logged in, redirect to respective dashboard
    if 'user_id' in session:
        current_role = session.get('role')
        if current_role == 'STUDENT':
            return redirect(url_for('student.dashboard'))
        elif current_role == 'FACULTY':
            return redirect(url_for('faculty.dashboard'))
        elif current_role == 'HOD':
            return redirect(url_for('hod.dashboard'))
        elif current_role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        login_identifier = (request.form.get('identifier') or request.form.get('email') or '').strip()
        password = request.form.get('password', '').strip()
        selected_role = request.form.get('role', target_role).upper()

        if not login_identifier or not password:
            flash('Please provide both identification (Email/ID) and password.', 'danger')
            return render_template('auth/login.html', active_role=selected_role)

        user = None

        if selected_role == 'STUDENT':
            # Check by email or student_id
            if '@' in login_identifier:
                user = User.query.filter_by(email=login_identifier, role='STUDENT', is_active=True).first()
            else:
                student_record = Student.query.filter_by(student_id=login_identifier).first()
                if student_record and student_record.user and student_record.user.is_active:
                    user = student_record.user

        elif selected_role == 'FACULTY':
            # Check by email or faculty_id
            if '@' in login_identifier:
                user = User.query.filter_by(email=login_identifier, role='FACULTY', is_active=True).first()
            else:
                faculty_record = Faculty.query.filter_by(faculty_id=login_identifier).first()
                if faculty_record and faculty_record.user and faculty_record.user.is_active:
                    user = faculty_record.user

        elif selected_role == 'HOD':
            user = User.query.filter_by(email=login_identifier, role='HOD', is_active=True).first()

        elif selected_role == 'ADMIN':
            user = User.query.filter_by(email=login_identifier, role='ADMIN', is_active=True).first()

        # Validate password & role
        if user and user.check_password(password):
            login_user_session(user)
            flash(f'Welcome back, {user.name}!', 'success')
            
            if user.role == 'STUDENT':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'FACULTY':
                return redirect(url_for('faculty.dashboard'))
            elif user.role == 'HOD':
                return redirect(url_for('hod.dashboard'))
            elif user.role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials or unauthorized role. Please check your details and try again.', 'danger')
            return render_template('auth/login.html', active_role=selected_role)

    return render_template('auth/login.html', active_role=target_role)

@auth_bp.route('/logout')
def logout():
    """Log out the current user."""
    logout_user_session()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login_view'))
