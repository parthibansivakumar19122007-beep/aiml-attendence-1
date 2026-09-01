from datetime import datetime
from sqlalchemy.orm import synonym
from . import db

class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id', ondelete='RESTRICT'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    session_date = synonym('date')
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='RESTRICT'), nullable=False)
    faculty_lat = db.Column(db.Numeric(10, 8), nullable=True)
    faculty_lng = db.Column(db.Numeric(11, 8), nullable=True)
    opened_at = db.Column(db.DateTime, nullable=False)
    closed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='OPEN', nullable=False) # 'OPEN', 'CLOSED', 'EXPIRED'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_sessions_date_status', 'date', 'status'),
        db.Index('idx_sessions_faculty', 'faculty_id', 'date'),
    )

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, *args, **kwargs):
        kwargs.pop('session_type', None)
        kwargs.pop('class_id', None)
        super().__init__(*args, **kwargs)

    @property
    def security_radius_m(self) -> float:
        return 50.0

    @property
    def class_id(self):
        return self.timetable_entry.class_id if self.timetable_entry else None

    @property
    def session_type(self) -> str:
        return 'HOURLY'

    def is_open(self) -> bool:
        return self.status == 'OPEN'

    def to_dict(self):
        return {
            'id': self.id,
            'timetable_id': self.timetable_id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'opened_at': self.opened_at.strftime('%Y-%m-%d %H:%M:%S') if self.opened_at else '',
            'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None,
            'status': self.status,
            'faculty_lat': float(self.faculty_lat) if self.faculty_lat is not None else None,
            'faculty_lng': float(self.faculty_lng) if self.faculty_lng is not None else None
        }

    def __repr__(self):
        return f"<AttendanceSession ID:{self.id} Date:{self.date} Status:{self.status}>"


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id', ondelete='CASCADE'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    attendance_type = db.Column(db.String(30), default='HOURLY_STUDENT', nullable=False) # 'HOURLY_STUDENT', 'MORNING_STUDENT'
    scanned_at = db.Column(db.DateTime, nullable=False) # Server timestamp of face recognition
    student_lat = db.Column(db.Numeric(10, 8), nullable=True)
    student_lng = db.Column(db.Numeric(11, 8), nullable=True)
    distance_m = db.Column(db.Numeric(8, 2), nullable=True)
    face_confidence = db.Column(db.Numeric(5, 4), nullable=True)
    status = db.Column(db.String(20), nullable=False) # 'PRESENT', 'REJECTED'
    rejection_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_session_student'),
        db.Index('idx_att_records_student', 'student_id', 'status'),
        db.Index('idx_att_records_session', 'session_id', 'status'),
        db.Index('idx_att_records_scanned_at', 'scanned_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_name': self.student.user.name if (self.student and self.student.user) else '',
            'student_roll': self.student.student_id if self.student else '',
            'attendance_type': self.attendance_type,
            'scanned_at': self.scanned_at.strftime('%Y-%m-%d %H:%M:%S') if self.scanned_at else '',
            'distance_m': float(self.distance_m) if self.distance_m is not None else None,
            'face_confidence': float(self.face_confidence) if self.face_confidence is not None else None,
            'status': self.status,
            'rejection_reason': self.rejection_reason
        }

    def __repr__(self):
        return f"<AttendanceRecord Student:{self.student_id} Status:{self.status}>"


class FacultyAttendance(db.Model):
    __tablename__ = 'faculty_attendance'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='CASCADE'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    attendance_type = db.Column(db.String(20), nullable=False) # 'MORNING', 'EVENING'
    scanned_at = db.Column(db.DateTime, nullable=False)
    latitude = db.Column(db.Numeric(10, 8), nullable=True)
    longitude = db.Column(db.Numeric(11, 8), nullable=True)
    status = db.Column(db.String(20), default='PRESENT', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('faculty_id', 'attendance_date', 'attendance_type', name='uq_faculty_daily_type'),
        db.Index('idx_faculty_att_lookup', 'attendance_date', 'attendance_type'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'faculty_name': self.faculty.user.name if (self.faculty and self.faculty.user) else '',
            'faculty_code': self.faculty.faculty_id if self.faculty else '',
            'attendance_date': self.attendance_date.strftime('%Y-%m-%d') if self.attendance_date else '',
            'attendance_type': self.attendance_type,
            'scanned_at': self.scanned_at.strftime('%Y-%m-%d %H:%M:%S') if self.scanned_at else '',
            'status': self.status
        }

    def __repr__(self):
        return f"<FacultyAttendance Fac:{self.faculty_id} Type:{self.attendance_type} Status:{self.status}>"
