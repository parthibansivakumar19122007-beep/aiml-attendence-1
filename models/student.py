from datetime import datetime
from . import db

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dept_code = db.Column(db.String(20), unique=True, nullable=False)
    dept_name = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    classes = db.relationship('ClassRoom', backref='department', lazy='dynamic')
    faculty_members = db.relationship('Faculty', backref='department', lazy='dynamic')

    def __repr__(self):
        return f"<Department {self.dept_code}>"


class ClassRoom(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    class_name = db.Column(db.String(80), nullable=False)           # 'I B.E II AIML'
    academic_year = db.Column(db.String(20), default='2026-2027', nullable=False)
    semester = db.Column(db.Integer, default=2, nullable=False)
    room_number = db.Column(db.String(40), default='Room 204', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('department_id', 'class_name', 'academic_year', name='uq_class_dept_name_year'),
    )

    # Relationships
    sections = db.relationship('Section', backref='classroom', lazy='dynamic', cascade='all, delete-orphan')
    students = db.relationship('Student', backref='classroom', lazy='dynamic')
    timetable_slots = db.relationship('Timetable', backref='classroom', lazy='dynamic')

    def __repr__(self):
        return f"<ClassRoom {self.class_name}>"


class Section(db.Model):
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False)
    section_name = db.Column(db.String(10), default='A', nullable=False)
    capacity = db.Column(db.Integer, default=60, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('class_id', 'section_name', name='uq_class_section'),
    )

    def __repr__(self):
        return f"<Section {self.section_name} (Class {self.class_id})>"


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True) # e.g. AIML001
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id', ondelete='RESTRICT'), nullable=False)
    year = db.Column(db.Integer, default=1, nullable=False)
    section = db.Column(db.String(10), default='A', nullable=False)
    photo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def barcode_value(self) -> str:
        return self.student_id

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.user.name if self.user else '',
            'student_id': self.student_id,
            'email': self.user.email if self.user else '',
            'class_name': self.classroom.class_name if self.classroom else '',
            'section': self.section,
            'year': self.year,
            'photo_path': self.photo_path
        }

    def __repr__(self):
        return f"<Student {self.student_id} - {self.user.name if self.user else ''}>"
