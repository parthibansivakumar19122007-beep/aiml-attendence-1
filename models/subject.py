from datetime import datetime
from . import db

class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    subject_name = db.Column(db.String(150), nullable=False)
    short_name = db.Column(db.String(40), nullable=False, index=True) # e.g. DSA, DM, COA
    credits = db.Column(db.Integer, default=3, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    timetable_slots = db.relationship('Timetable', backref='subject', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'subject_code': self.subject_code,
            'subject_name': self.subject_name,
            'short_name': self.short_name,
            'credits': self.credits,
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<Subject {self.short_name} ({self.subject_code})>"
