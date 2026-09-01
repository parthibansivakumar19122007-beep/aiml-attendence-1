from .auth import auth_bp
from .student import student_bp
from .faculty import faculty_bp
from .hod import hod_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'student_bp', 'faculty_bp', 'hod_bp', 'admin_bp']
