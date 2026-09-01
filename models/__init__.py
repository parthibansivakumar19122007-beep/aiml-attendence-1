from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User, FaceEmbedding
from .student import Department, ClassRoom, Section, Student
from .faculty import Faculty
from .subject import Subject
from .timetable import Timetable
from .attendance import AttendanceSession, AttendanceRecord, FacultyAttendance
from .audit import AuditLog

__all__ = [
    'db',
    'User',
    'FaceEmbedding',
    'Department',
    'ClassRoom',
    'Section',
    'Student',
    'Faculty',
    'Subject',
    'Timetable',
    'AttendanceSession',
    'AttendanceRecord',
    'FacultyAttendance',
    'AuditLog'
]
