from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User
from services.auth_service import login_user_session, logout_user_session, authenticate_user

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
    return redirect(url_for('auth.login_view'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_view():
    """
    Single unified login view for all 4 roles (STUDENT, FACULTY, HOD, ADMIN).
    Validates username and password, looks up the user, and automatically
    redirects to the appropriate portal according to their role in the database.
    """
    # If already logged in, redirect to respective role dashboard
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
        # Accept username or backward-compatible identifier/email
        username = (request.form.get('username') or request.form.get('identifier') or request.form.get('email') or '').strip()
        password = request.form.get('password', '').strip()

        user, error = authenticate_user(username, password)
        if user:
            login_user_session(user)
            flash(f'Welcome back, {user.name}!', 'success')
            
            # Role comes strictly from the database entity
            if user.role == 'STUDENT':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'FACULTY':
                return redirect(url_for('faculty.dashboard'))
            elif user.role == 'HOD':
                return redirect(url_for('hod.dashboard'))
            elif user.role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Unknown user role assigned. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.login_view'))
        else:
            flash(error or 'Invalid credentials. Please check your username and password.', 'danger')
            return render_template('auth/login.html', entered_username=username)

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Log out the current user and clear session."""
    logout_user_session()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login_view'))
