from datetime import datetime
from . import db

class Timetable(db.Model):
    __tablename__ = 'timetable'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    academic_year = db.Column(db.String(20), default='2026-2027', nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    day_of_week = db.Column(
        db.Enum('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', name='timetable_days'), 
        nullable=False
    )
    hour_number = db.Column(db.SmallInteger, nullable=False) # 1 to 7
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='RESTRICT'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id', ondelete='RESTRICT'), nullable=False)
    start_time = db.Column(db.Time, nullable=False) # e.g. 09:10:00
    end_time = db.Column(db.Time, nullable=False)   # e.g. 10:00:00
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'academic_year', 'class_id', 'day_of_week', 'hour_number', 'subject_id', 'faculty_id', 
            name='uq_timetable_slot'
        ),
        db.Index('idx_tt_lookup', 'day_of_week', 'hour_number', 'is_active'),
        db.Index('idx_tt_faculty_lookup', 'faculty_id', 'day_of_week', 'is_active'),
    )

    # Relationships
    attendance_sessions = db.relationship('AttendanceSession', backref='timetable_entry', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'academic_year': self.academic_year,
            'day_of_week': self.day_of_week,
            'hour_number': self.hour_number,
            'start_time': self.start_time.strftime('%I:%M %p') if self.start_time else '',
            'end_time': self.end_time.strftime('%I:%M %p') if self.end_time else '',
            'subject_name': self.subject.subject_name if self.subject else '',
            'subject_short': self.subject.short_name if self.subject else '',
            'faculty_name': self.faculty.user.name if (self.faculty and self.faculty.user) else '',
            'class_name': self.classroom.class_name if self.classroom else '',
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<Timetable {self.day_of_week} H{self.hour_number} - {self.subject.short_name if self.subject else ''}>"
