-- =====================================================================================
-- AIML SMART FACE RECOGNITION ATTENDANCE MANAGEMENT SYSTEM
-- Institution: Nehru Institute of Technology (Autonomous)
-- Department: CSE - Artificial Intelligence and Machine Learning
-- Class: I B.E II AIML | Academic Year: 2026-2027
-- Database Engine: MySQL 8.0+ / MariaDB / SQLite compatible
-- =====================================================================================

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS faculty_attendance;
DROP TABLE IF EXISTS attendance_records;
DROP TABLE IF EXISTS attendance_sessions;
DROP TABLE IF EXISTS face_embeddings;
DROP TABLE IF EXISTS timetable;
DROP TABLE IF EXISTS subjects;
DROP TABLE IF EXISTS faculty;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS sections;
DROP TABLE IF EXISTS classes;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS users;

-- -------------------------------------------------------------------------------------
-- 1. USERS TABLE (Core Authentication & Role-Based Access Control)
-- Roles: STUDENT, FACULTY, HOD, ADMIN
-- -------------------------------------------------------------------------------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_user_role CHECK (role IN ('STUDENT', 'FACULTY', 'HOD', 'ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- -------------------------------------------------------------------------------------
-- 2. DEPARTMENTS TABLE
-- -------------------------------------------------------------------------------------
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dept_code VARCHAR(20) NOT NULL UNIQUE,
    dept_name VARCHAR(150) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------------------
-- 3. CLASSES TABLE
-- -------------------------------------------------------------------------------------
CREATE TABLE classes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department_id INT NOT NULL,
    class_name VARCHAR(80) NOT NULL,
    academic_year VARCHAR(20) NOT NULL DEFAULT '2026-2027',
    semester INT NOT NULL DEFAULT 2,
    room_number VARCHAR(40) NOT NULL DEFAULT 'Room 204',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    CONSTRAINT uq_class_dept_name_year UNIQUE (department_id, class_name, academic_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------------------
-- 4. SECTIONS TABLE
-- -------------------------------------------------------------------------------------
CREATE TABLE sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    section_name VARCHAR(10) NOT NULL DEFAULT 'A',
    capacity INT NOT NULL DEFAULT 60,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    CONSTRAINT uq_class_section UNIQUE (class_id, section_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------------------------------
-- 5. STUDENTS TABLE (Extends Users with Academic & Photo Profile)
-- -------------------------------------------------------------------------------------
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    student_id VARCHAR(50) NOT NULL UNIQUE,
    class_id INT NOT NULL,
    year INT NOT NULL DEFAULT 1,
    section VARCHAR(10) NOT NULL DEFAULT 'A',
    photo_path VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_students_student_id ON students(student_id);
CREATE INDEX idx_students_class ON students(class_id, section);

-- -------------------------------------------------------------------------------------
-- 6. FACULTY TABLE (Extends Users with Academic Department Profile)
-- -------------------------------------------------------------------------------------
CREATE TABLE faculty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    faculty_id VARCHAR(50) NOT NULL UNIQUE,
    department_id INT NOT NULL,
    designation VARCHAR(80) NOT NULL DEFAULT 'Assistant Professor',
    photo_path VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_faculty_faculty_id ON faculty(faculty_id);

-- -------------------------------------------------------------------------------------
-- 7. FACE EMBEDDINGS TABLE (Secure 128/512-dim Vector Embeddings for Face Recognition)
-- -------------------------------------------------------------------------------------
CREATE TABLE face_embeddings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    embedding_data JSON NOT NULL,
    model_name VARCHAR(80) NOT NULL DEFAULT 'face_recognition_v1',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_face_embeddings_user ON face_embeddings(user_id, is_active);

-- -------------------------------------------------------------------------------------
-- 8. SUBJECTS MASTER TABLE
-- -------------------------------------------------------------------------------------
CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(30) NOT NULL UNIQUE,
    subject_name VARCHAR(150) NOT NULL,
    short_name VARCHAR(40) NOT NULL,
    credits INT NOT NULL DEFAULT 3,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_subjects_code ON subjects(subject_code);
CREATE INDEX idx_subjects_short ON subjects(short_name);

-- -------------------------------------------------------------------------------------
-- 9. TIMETABLE MASTER TABLE (42 Weekly Slots Monday-Saturday)
-- -------------------------------------------------------------------------------------
CREATE TABLE timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day_of_week VARCHAR(20) NOT NULL,
    class_id INT NOT NULL,
    hour_number INT NOT NULL,
    subject_id INT NOT NULL,
    faculty_id INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    academic_year VARCHAR(20) NOT NULL DEFAULT '2026-2027',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE RESTRICT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE RESTRICT,
    CONSTRAINT uq_timetable_class_slot UNIQUE (day_of_week, class_id, hour_number, academic_year),
    CONSTRAINT uq_timetable_faculty_slot UNIQUE (day_of_week, faculty_id, hour_number, academic_year),
    CONSTRAINT chk_day_of_week CHECK (day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')),
    CONSTRAINT chk_hour_number CHECK (hour_number BETWEEN 1 AND 7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_timetable_lookup ON timetable(day_of_week, hour_number, is_active);
CREATE INDEX idx_timetable_faculty ON timetable(faculty_id, day_of_week);

-- -------------------------------------------------------------------------------------
-- 10. ATTENDANCE SESSIONS TABLE (Live Hourly Attendance Instances Opened by Faculty)
-- -------------------------------------------------------------------------------------
CREATE TABLE attendance_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timetable_id INT NOT NULL,
    date DATE NOT NULL,
    faculty_id INT NOT NULL,
    faculty_lat DECIMAL(10, 8) NULL,
    faculty_lng DECIMAL(11, 8) NULL,
    opened_at DATETIME NOT NULL,
    closed_at DATETIME NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (timetable_id) REFERENCES timetable(id) ON DELETE RESTRICT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE RESTRICT,
    CONSTRAINT chk_session_status CHECK (status IN ('OPEN', 'CLOSED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_sessions_date_status ON attendance_sessions(date, status);
CREATE INDEX idx_sessions_faculty ON attendance_sessions(faculty_id, date);

-- -------------------------------------------------------------------------------------
-- 11. ATTENDANCE RECORDS TABLE (Individual Student Face Attendance Records)
-- -------------------------------------------------------------------------------------
CREATE TABLE attendance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NULL,
    student_id INT NOT NULL,
    attendance_type VARCHAR(30) NOT NULL DEFAULT 'HOURLY_STUDENT',
    scanned_at DATETIME NOT NULL,
    student_lat DECIMAL(10, 8) NULL,
    student_lng DECIMAL(11, 8) NULL,
    distance_m DECIMAL(8, 2) NULL,
    face_confidence DECIMAL(5, 4) NULL,
    status VARCHAR(20) NOT NULL,
    rejection_reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    CONSTRAINT uq_session_student UNIQUE (session_id, student_id),
    CONSTRAINT chk_record_status CHECK (status IN ('PRESENT', 'REJECTED')),
    CONSTRAINT chk_att_type CHECK (attendance_type IN ('HOURLY_STUDENT', 'MORNING_STUDENT'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_att_records_student ON attendance_records(student_id, status);
CREATE INDEX idx_att_records_session ON attendance_records(session_id, status);
CREATE INDEX idx_att_records_scanned_at ON attendance_records(scanned_at);

-- -------------------------------------------------------------------------------------
-- 12. FACULTY ATTENDANCE TABLE (Faculty Morning Check-in & Evening Check-out)
-- -------------------------------------------------------------------------------------
CREATE TABLE faculty_attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    attendance_type VARCHAR(20) NOT NULL,
    scanned_at DATETIME NOT NULL,
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PRESENT',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    CONSTRAINT uq_faculty_daily_type UNIQUE (faculty_id, attendance_date, attendance_type),
    CONSTRAINT chk_fac_att_type CHECK (attendance_type IN ('MORNING', 'EVENING')),
    CONSTRAINT chk_fac_status CHECK (status IN ('PRESENT', 'REJECTED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_faculty_att_lookup ON faculty_attendance(attendance_date, attendance_type);

-- -------------------------------------------------------------------------------------
-- 13. AUDIT LOGS TABLE (Comprehensive System & Security Event Tracking)
-- -------------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(80) NOT NULL,
    session_id INT NULL,
    record_id INT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);
