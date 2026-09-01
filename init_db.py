"""
Database Initialization and Seed Script
Populates the database with official Nehru Institute of Technology AIML department data:
- Roles: ADMIN, HOD, 9 FACULTY, 5 STUDENTS
- 16 Subjects
- Full 42-slot Mon-Sat Timetable
- Initial Face Embeddings
Supports MySQL and automatic SQLite local fallback.
"""

import os
from datetime import time
from app import create_app
from models import db, User, Department, ClassRoom, Section, Student, Faculty, Subject, Timetable, FaceEmbedding

def initialize_database():
    app = create_app()
    
    with app.app_context():
        try:
            print(f"Connecting to database: {app.config['SQLALCHEMY_DATABASE_URI']} ...")
            db.create_all()
            print("Database schema synchronized successfully.")
        except Exception as e:
            print(f"Warning: Primary database connection failed ({e}).")
            print("Switching to SQLite local database (sqlite:///aiml_attendance.db)...")
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aiml_attendance.db'
            db.init_app(app)
            db.create_all()
            print("SQLite schema created successfully.")

        # Check if users already exist
        if User.query.first():
            print("Database already contains seed data. Skipping seed process.")
            return

        print("Seeding Department, Class, and Section...")
        dept = Department(
            dept_code='CSE-AIML',
            dept_name='Computer Science and Engineering (Artificial Intelligence and Machine Learning)'
        )
        db.session.add(dept)
        db.session.flush()

        classroom = ClassRoom(
            department_id=dept.id,
            class_name='I B.E II AIML',
            academic_year='2026-2027',
            semester=2,
            room_number='Room 204'
        )
        db.session.add(classroom)
        db.session.flush()

        sec = Section(
            class_id=classroom.id,
            section_name='A',
            capacity=60
        )
        db.session.add(sec)
        db.session.flush()

        print("Seeding 16 Curriculum Subjects...")
        subjects_data = [
            ('MA3354', 'DISCRETE MATHEMATICS FOR COMPUTING', 'DM', 4),
            ('CS3351', 'DATA STRUCTURES AND ALGORITHMS', 'DSA', 3),
            ('CS3391', 'OBJECT ORIENTED PROGRAMMING USING JAVA', 'OOPS', 3),
            ('CS3352', 'COMPUTER ORGANIZATION AND ARCHITECTURE', 'COA', 3),
            ('CS3361', 'COMPUTER ORGANIZATION AND ARCHITECTURE LAB', 'COA LAB', 2),
            ('CS3381', 'DATA STRUCTURES LAB', 'DS LAB', 2),
            ('CS3382', 'JAVA PROGRAMMING LAB', 'JAVA LAB', 2),
            ('AD3351', 'FOUNDATIONS OF DATA SCIENCE', 'FDS', 3),
            ('AD3361', 'FOUNDATIONS OF DATA SCIENCE LAB', 'FDS LAB', 2),
            ('MC3301', 'LIFE SKILLS AND ETHICS', 'MC', 2),
            ('VE3301', 'VOCATIONAL ENHANCEMENT TRAINING', 'VEC', 1),
            ('HS3301', 'APTITUDE AND COMMUNICATION FOR ENGINEERS', 'APT/COMM', 2),
            ('TW3301', 'TUTOR WARD MEETING', 'TWM', 1),
            ('LB3301', 'LIBRARY', 'LIB', 1),
            ('IC3301', 'IIC ACTIVITY', 'IIC', 1),
            ('CS3392', 'JAVA PROGRAMMING', 'JAVA', 3),
        ]
        sub_dict = {}
        for code, name, short, cr in subjects_data:
            s = Subject(subject_code=code, subject_name=name, short_name=short, credits=cr)
            db.session.add(s)
            db.session.flush()
            sub_dict[short] = s

        print("Seeding Admin User...")
        admin_user = User(
            role='ADMIN',
            name='System Administrator',
            email='admin@example.com'
        )
        admin_user.set_password('Password123!')
        db.session.add(admin_user)

        print("Seeding HOD User...")
        hod_user = User(
            role='HOD',
            name='Dr. S. Ananthi',
            email='hod@example.com'
        )
        hod_user.set_password('Password123!')
        db.session.add(hod_user)

        print("Seeding 9 Faculty Members...")
        faculty_data = [
            ('Dr. A. Shobana', 'shobana@example.com', 'FAC_AIML_001', 'Associate Professor', 'uploads/faculty/shobana.jpg'),
            ('Mr. M. Eshwar Vadivel', 'eswar@example.com', 'FAC_AIML_002', 'Assistant Professor', 'uploads/faculty/eshwar.jpg'),
            ('Mr. V. Nagaraj', 'nagaraj@example.com', 'FAC_AIML_003', 'Assistant Professor', 'uploads/faculty/nagaraj.jpg'),
            ('Mrs. M. Nansiyaz Banu', 'nansiyaz@example.com', 'FAC_AIML_004', 'Assistant Professor', 'uploads/faculty/nansiyaz.jpg'),
            ('Dr. S. Jyothi Lakshmi', 'jyothi@example.com', 'FAC_AIML_005', 'Associate Professor', 'uploads/faculty/jyothi.jpg'),
            ('Mr. S. Udhayakumar', 'udhayakumar@example.com', 'FAC_AIML_006', 'Assistant Professor', 'uploads/faculty/udhayakumar.jpg'),
            ('Mrs. P. Gokilamani', 'gokilamani@example.com', 'FAC_AIML_007', 'Assistant Professor', 'uploads/faculty/gokilamani.jpg'),
            ('Dr. M. Bhuvaneswari', 'bhuvaneswari@example.com', 'FAC_AIML_008', 'Professor', 'uploads/faculty/bhuvaneswari.jpg'),
            ('Mr. V. Nagaraju', 'nagaraju@example.com', 'FAC_AIML_009', 'Assistant Professor', 'uploads/faculty/nagaraju.jpg'),
        ]
        fac_dict = {}
        for name, email, fac_id, desig, photo in faculty_data:
            u = User(role='FACULTY', name=name, email=email)
            u.set_password('Password123!')
            db.session.add(u)
            db.session.flush()

            f = Faculty(user_id=u.id, faculty_id=fac_id, department_id=dept.id, designation=desig, photo_path=photo)
            db.session.add(f)
            db.session.flush()
            fac_dict[name] = f

        print("Seeding 5 Students & Face Embeddings...")
        students_data = [
            ('Parthiban', 'student@example.com', 'AIML001', 'uploads/students/AIML001.jpg'),
            ('Aarav Sharma', 'aarav@example.com', 'AIML002', 'uploads/students/AIML002.jpg'),
            ('Kavya Nair', 'kavya@example.com', 'AIML003', 'uploads/students/AIML003.jpg'),
            ('Rahul Verma', 'rahul@example.com', 'AIML004', 'uploads/students/AIML004.jpg'),
            ('Priya Dharshini', 'priya@example.com', 'AIML005', 'uploads/students/AIML005.jpg'),
        ]
        dummy_vector = [0.05 * (i % 10) - 0.02 for i in range(128)]
        for name, email, roll, photo in students_data:
            u = User(role='STUDENT', name=name, email=email)
            u.set_password('Password123!')
            db.session.add(u)
            db.session.flush()

            st = Student(user_id=u.id, student_id=roll, class_id=classroom.id, year=1, section='A', photo_path=photo)
            db.session.add(st)
            
            fe = FaceEmbedding(user_id=u.id, embedding_data=dummy_vector, model_name='face_recognition_v1', is_active=True)
            db.session.add(fe)

        print("Seeding Official Monday - Saturday 42-Hour Timetable Schedule...")
        hour_timings = {
            1: (time(9, 10), time(10, 0)),
            2: (time(10, 0), time(10, 50)),
            3: (time(11, 10), time(12, 0)),
            4: (time(12, 0), time(12, 50)),
            5: (time(13, 40), time(14, 30)),
            6: (time(14, 30), time(15, 20)),
            7: (time(15, 20), time(16, 10))
        }

        schedule = [
            # Monday
            ('Monday', 1, 'FDS', 'Mrs. P. Gokilamani'),
            ('Monday', 2, 'DSA', 'Mr. M. Eshwar Vadivel'),
            ('Monday', 3, 'DM', 'Dr. A. Shobana'),
            ('Monday', 4, 'MC', 'Mrs. P. Gokilamani'),
            ('Monday', 5, 'DSA', 'Mr. M. Eshwar Vadivel'),
            ('Monday', 6, 'COA', 'Dr. S. Jyothi Lakshmi'),
            ('Monday', 7, 'APT/COMM', 'Dr. M. Bhuvaneswari'),

            # Tuesday
            ('Tuesday', 1, 'COA', 'Mrs. M. Nansiyaz Banu'),
            ('Tuesday', 2, 'IIC', 'Mrs. P. Gokilamani'),
            ('Tuesday', 3, 'COA', 'Dr. S. Jyothi Lakshmi'),
            ('Tuesday', 4, 'DS LAB', 'Mr. S. Udhayakumar'),
            ('Tuesday', 5, 'DS LAB', 'Mr. S. Udhayakumar'),
            ('Tuesday', 6, 'DS LAB', 'Mr. S. Udhayakumar'),
            ('Tuesday', 7, 'LIB', 'Mr. S. Udhayakumar'),

            # Wednesday
            ('Wednesday', 1, 'COA LAB', 'Mrs. M. Nansiyaz Banu'),
            ('Wednesday', 2, 'COA LAB', 'Dr. S. Jyothi Lakshmi'),
            ('Wednesday', 3, 'DM', 'Dr. A. Shobana'),
            ('Wednesday', 4, 'DSA', 'Mr. M. Eshwar Vadivel'),
            ('Wednesday', 5, 'FDS', 'Mrs. P. Gokilamani'),
            ('Wednesday', 6, 'APT/COMM', 'Dr. M. Bhuvaneswari'),
            ('Wednesday', 7, 'APT/COMM', 'Mrs. P. Gokilamani'),

            # Thursday
            ('Thursday', 1, 'DSA', 'Mr. M. Eshwar Vadivel'),
            ('Thursday', 2, 'DM', 'Dr. A. Shobana'),
            ('Thursday', 3, 'FDS LAB', 'Mrs. P. Gokilamani'),
            ('Thursday', 4, 'FDS LAB', 'Mrs. P. Gokilamani'),
            ('Thursday', 5, 'DM', 'Dr. A. Shobana'),
            ('Thursday', 6, 'VEC', 'Mrs. P. Gokilamani'),
            ('Thursday', 7, 'VEC', 'Mrs. P. Gokilamani'),

            # Friday
            ('Friday', 1, 'DM', 'Dr. A. Shobana'),
            ('Friday', 2, 'COA', 'Mrs. M. Nansiyaz Banu'),
            ('Friday', 3, 'FDS', 'Mrs. P. Gokilamani'),
            ('Friday', 4, 'DM', 'Dr. A. Shobana'),
            ('Friday', 5, 'LIB', 'Mr. S. Udhayakumar'),
            ('Friday', 6, 'MC', 'Mrs. P. Gokilamani'),
            ('Friday', 7, 'TWM', 'Mr. M. Eshwar Vadivel'),

            # Saturday
            ('Saturday', 1, 'OOPS', 'Mr. V. Nagaraj'),
            ('Saturday', 2, 'OOPS', 'Mr. V. Nagaraj'),
            ('Saturday', 3, 'OOPS', 'Mr. V. Nagaraj'),
            ('Saturday', 4, 'JAVA', 'Mr. V. Nagaraju'),
            ('Saturday', 5, 'JAVA LAB', 'Mr. V. Nagaraju'),
            ('Saturday', 6, 'JAVA LAB', 'Mr. V. Nagaraju'),
            ('Saturday', 7, 'JAVA LAB', 'Mr. V. Nagaraju'),
        ]

        for day, hr, sub_key, fac_key in schedule:
            s_obj = sub_dict.get(sub_key)
            f_obj = fac_dict.get(fac_key)
            t_start, t_end = hour_timings[hr]
            
            slot = Timetable(
                academic_year='2026-2027',
                class_id=classroom.id,
                day_of_week=day,
                hour_number=hr,
                subject_id=s_obj.id,
                faculty_id=f_obj.id,
                start_time=t_start,
                end_time=t_end,
                is_active=True
            )
            db.session.add(slot)

        db.session.commit()
        print("SUCCESS: Database initialized with Admin, HOD, Faculty, Students, Face Embeddings, and Timetable!")

if __name__ == '__main__':
    initialize_database()
