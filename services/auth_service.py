from functools import wraps
from flask import session, redirect, url_for, flash, request
from models import db, User, AuditLog

def login_user_session(user: User):
    """Store user identification and role securely in Flask session."""
    session.clear()
    session['user_id'] = user.id
    session['role'] = user.role
    session['name'] = user.name
    session['email'] = user.email
    session.permanent = True

    # Log login action
    try:
        log = AuditLog(
            user_id=user.id,
            action=f"{user.role}_LOGIN_SUCCESS",
            details=f"User {user.email} logged in successfully.",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

def logout_user_session():
    """Clear session data and record logout in audit log."""
    user_id = session.get('user_id')
    user_email = session.get('email', 'Unknown')
    role = session.get('role', 'UNKNOWN')

    if user_id:
        try:
            log = AuditLog(
                user_id=user_id,
                action=f"{role}_LOGOUT",
                details=f"User {user_email} logged out.",
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

def login_required(f):
    """Decorator to enforce that a user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login_view'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to enforce 4-role based access control (STUDENT, FACULTY, HOD, ADMIN)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login_view'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f'Access denied: You do not have permissions for the {", ".join(allowed_roles)} portal.', 'danger')
                
                # Redirect to respective role home
                if user_role == 'STUDENT':
                    return redirect(url_for('student.dashboard'))
                elif user_role == 'FACULTY':
                    return redirect(url_for('faculty.dashboard'))
                elif user_role == 'HOD':
                    return redirect(url_for('hod.dashboard'))
                elif user_role == 'ADMIN':
                    return redirect(url_for('admin.dashboard'))
                else:
                    session.clear()
                    return redirect(url_for('auth.login_view'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
