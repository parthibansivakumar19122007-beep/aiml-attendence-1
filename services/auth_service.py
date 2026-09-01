from functools import wraps
from flask import session, redirect, url_for, flash, request, render_template, jsonify
from models import db, User, Student, Faculty, AuditLog

def login_user_session(user: User):
    """Store user identification and role securely in Flask session."""
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['name'] = user.name
    session['email'] = user.email
    session['department'] = getattr(user, 'department', 'CSE-AIML')
    session.permanent = True

    # Log login action
    try:
        log = AuditLog(
            user_id=user.id,
            action=f"{user.role}_LOGIN_SUCCESS",
            details=f"User {user.username} ({user.email}) logged in successfully.",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

def logout_user_session():
    """Clear session data and record logout in audit log."""
    user_id = session.get('user_id')
    username = session.get('username') or session.get('email', 'Unknown')
    role = session.get('role', 'UNKNOWN')

    if user_id:
        try:
            log = AuditLog(
                user_id=user_id,
                action=f"{role}_LOGOUT",
                details=f"User {username} logged out.",
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()

    session.clear()

def get_current_user():
    """Retrieve active User instance from database using session data."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.filter_by(id=user_id, is_active=True).first()

def authenticate_user(login_identifier: str, password: str):
    """
    Authenticate user by username, email, student_id, or faculty_id.
    Validates password hash and active status.
    Returns (user, error_message).
    """
    if not login_identifier or not password:
        return None, "Please provide both username and password."

    clean_id = login_identifier.strip()
    user = None

    # 1. Check exact username match
    user = User.query.filter_by(username=clean_id).first()

    # 2. If not found, check email match
    if not user and '@' in clean_id:
        user = User.query.filter_by(email=clean_id.lower()).first()

    # 3. If not found, check Student ID (e.g. AIML001)
    if not user:
        student_rec = Student.query.filter_by(student_id=clean_id.upper()).first()
        if student_rec and student_rec.user:
            user = student_rec.user

    # 4. If not found, check Faculty ID (e.g. FAC_AIML_001)
    if not user:
        fac_rec = Faculty.query.filter_by(faculty_id=clean_id.upper()).first()
        if fac_rec and fac_rec.user:
            user = fac_rec.user

    if not user:
        return None, "Account not found. Please verify your credentials."

    if not user.is_active or getattr(user, 'status', 'ACTIVE') == 'INACTIVE':
        return None, "This account is currently deactivated. Please contact the administrator."

    if not user.check_password(password):
        return None, "Invalid credentials. Incorrect password. Please try again."

    return user, None

def login_required(f):
    """Decorator to enforce that a user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login_view'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to enforce strict 4-role based access control (STUDENT, FACULTY, HOD, ADMIN).
    Returns 403 Forbidden with dedicated error template or JSON response upon unauthorized access.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login_view'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                # Log security violation
                try:
                    log = AuditLog(
                        user_id=session.get('user_id'),
                        action="UNAUTHORIZED_ACCESS_ATTEMPT",
                        details=f"User {session.get('username')} ({user_role}) attempted to access {request.path} requiring {allowed_roles}",
                        ip_address=request.remote_addr
                    )
                    db.session.add(log)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                # API / JSON response
                if request.is_json or request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({
                        'error': 'Forbidden',
                        'message': f'Access denied: {", ".join(allowed_roles)} role required.',
                        'status': 403
                    }), 403

                # Render strict 403 Forbidden page
                return render_template('errors/403.html', allowed_roles=allowed_roles), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
