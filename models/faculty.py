from datetime import datetime
from . import db

class Faculty(db.Model):
    __tablename__ = 'faculty'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    faculty_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. FAC_AIML_001
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='RESTRICT'), nullable=False)
    designation = db.Column(db.String(80), default='Assistant Professor', nullable=False)
    photo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    timetable_slots = db.relationship('Timetable', backref='faculty', lazy='dynamic')
    attendance_sessions = db.relationship('AttendanceSession', backref='faculty', lazy='dynamic')
    faculty_attendance = db.relationship('FacultyAttendance', backref='faculty', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def barcode_value(self) -> str:
        return self.faculty_id

    def to_dict(self):
        return {
            'id': self.id,
            'faculty_id': self.faculty_id,
            'name': self.user.name if self.user else '',
            'email': self.user.email if self.user else '',
            'designation': self.designation,
            'department': self.department.dept_code if self.department else '',
            'photo_path': self.photo_path
        }

    def __repr__(self):
        return f"<Faculty {self.faculty_id} - {self.user.name if self.user else ''}>"
