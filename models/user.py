from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(db.Model):
    """Core User entity with 4-Role RBAC (STUDENT, FACULTY, HOD, ADMIN) and secure password hashing."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False) # 'STUDENT', 'FACULTY', 'HOD', 'ADMIN'
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    department = db.Column(db.String(120), default='CSE-AIML', nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    faculty_profile = db.relationship('Faculty', backref='user', uselist=False, cascade='all, delete-orphan')
    face_embeddings = db.relationship('FaceEmbedding', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password: str):
        """Hash password using Werkzeug's secure hashing algorithm."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify plain password against hashed password."""
        return check_password_hash(self.password_hash, password)

    def is_student(self) -> bool:
        return self.role == 'STUDENT'

    def is_faculty(self) -> bool:
        return self.role == 'FACULTY'

    def is_hod(self) -> bool:
        return self.role == 'HOD'

    def is_admin(self) -> bool:
        return self.role == 'ADMIN'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'status': self.status,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

    def __repr__(self):
        return f"<User {self.username} - {self.email} ({self.role})>"


class FaceEmbedding(db.Model):
    """Stores 128/512-dimensional face recognition vector embeddings."""
    __tablename__ = 'face_embeddings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    embedding_data = db.Column(db.JSON, nullable=False) # Serialized list of floats
    model_name = db.Column(db.String(80), default='face_recognition_v1', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'model_name': self.model_name,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

    def __repr__(self):
        return f"<FaceEmbedding User:{self.user_id} Model:{self.model_name}>"
