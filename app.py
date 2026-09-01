import os
from datetime import datetime
import pytz
from flask import Flask, render_template, redirect, url_for, session
from flask_migrate import Migrate
from config import Config
from models import db, User, Department, ClassRoom, Student, Faculty, Subject, Timetable, AttendanceSession, AttendanceRecord, FacultyAttendance, AuditLog
from routes import auth_bp, student_bp, faculty_bp, hod_bp, admin_bp

def create_app(config_class=Config):
    """Application factory for AIML Smart Attendance System."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(hod_bp)
    app.register_blueprint(admin_bp)

    # Context processors for global templates
    @app.context_processor
    def inject_global_vars():
        tz = pytz.timezone(app.config.get('TIMEZONE', 'Asia/Kolkata'))
        now_ist = datetime.now(tz)
        return {
            'college_name': app.config.get('COLLEGE_NAME'),
            'dept_name': app.config.get('DEPARTMENT_NAME'),
            'class_name': app.config.get('CLASS_NAME'),
            'academic_year': app.config.get('ACADEMIC_YEAR'),
            'server_ist_time': now_ist.strftime('%I:%M %p'),
            'server_ist_date': now_ist.strftime('%d-%m-%Y'),
            'geofence_radius': app.config.get('DEFAULT_GEOFENCE_RADIUS_METERS')
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html'), 404

    @app.errorhandler(403)
    def access_forbidden(e):
        return render_template('base.html'), 403

    return app

app = create_app()

if __name__ == '__main__':
    # Local development server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
