-- =====================================================================================
-- AIML SMART FACE RECOGNITION ATTENDANCE MANAGEMENT SYSTEM - SEED DATASET
-- Institution: Nehru Institute of Technology (Autonomous)
-- Department: CSE – Artificial Intelligence and Machine Learning
-- Class: I B.E II AIML (Academic Year: 2026-2027)
-- =====================================================================================

-- 1. DEPARTMENT
INSERT INTO departments (id, dept_code, dept_name) VALUES
(1, 'CSE-AIML', 'Computer Science and Engineering (Artificial Intelligence and Machine Learning)');

-- 2. CLASSROOM & SECTION
INSERT INTO classes (id, department_id, class_name, academic_year, semester, room_number) VALUES
(1, 1, 'I B.E II AIML', '2026-2027', 2, 'Room 204');

INSERT INTO sections (id, class_id, section_name, capacity) VALUES
(1, 1, 'A', 60);

-- 3. USERS (ADMIN, HOD, FACULTY, STUDENTS)
-- Default Password for all seed users: Password123!
-- Scrypt hash: scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02

-- 3.1 Admin User
INSERT INTO users (id, role, name, email, password_hash, is_active) VALUES
(1, 'ADMIN', 'System Administrator', 'admin@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE);

-- 3.2 HOD User
INSERT INTO users (id, role, name, email, password_hash, is_active) VALUES
(2, 'HOD', 'Dr. S. Ananthi', 'hod@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE);

-- 3.3 Faculty Users (9 Faculty members matching Master Data)
INSERT INTO users (id, role, name, email, password_hash, is_active) VALUES
(3, 'FACULTY', 'Dr. A. Shobana', 'shobana@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(4, 'FACULTY', 'Mr. M. Eshwar Vadivel', 'eswar@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(5, 'FACULTY', 'Mr. V. Nagaraj', 'nagaraj@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(6, 'FACULTY', 'Mrs. M. Nansiyaz Banu', 'nansiyaz@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(7, 'FACULTY', 'Dr. S. Jyothi Lakshmi', 'jyothi@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(8, 'FACULTY', 'Mr. S. Udhayakumar', 'udhayakumar@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(9, 'FACULTY', 'Mrs. P. Gokilamani', 'gokilamani@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(10, 'FACULTY', 'Dr. M. Bhuvaneswari', 'bhuvaneswari@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(11, 'FACULTY', 'Mr. V. Nagaraju', 'nagaraju@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE);

-- 3.4 Student Users (5 Students)
INSERT INTO users (id, role, name, email, password_hash, is_active) VALUES
(12, 'STUDENT', 'Parthiban', 'student@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(13, 'STUDENT', 'Aarav Sharma', 'aarav@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(14, 'STUDENT', 'Kavya Nair', 'kavya@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(15, 'STUDENT', 'Rahul Verma', 'rahul@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE),
(16, 'STUDENT', 'Priya Dharshini', 'priya@example.com', 'scrypt:32768:8:1$kX6uH1yN7lFjF4z2$9e120f26fffae7baec28a8d11cbe8d20eeef4cfec1bcebaecbfdf0eb038b3400a40ffbfa6933bbecaaae45b34da5db0d603a11df6fc7c6a9ea1ff29d91f16c02', TRUE);

-- 4. FACULTY DETAILS
INSERT INTO faculty (id, user_id, faculty_id, department_id, designation, photo_path) VALUES
(1, 3, 'FAC_AIML_001', 1, 'Associate Professor', 'uploads/faculty/shobana.jpg'),
(2, 4, 'FAC_AIML_002', 1, 'Assistant Professor', 'uploads/faculty/eshwar.jpg'),
(3, 5, 'FAC_AIML_003', 1, 'Assistant Professor', 'uploads/faculty/nagaraj.jpg'),
(4, 6, 'FAC_AIML_004', 1, 'Assistant Professor', 'uploads/faculty/nansiyaz.jpg'),
(5, 7, 'FAC_AIML_005', 1, 'Associate Professor', 'uploads/faculty/jyothi.jpg'),
(6, 8, 'FAC_AIML_006', 1, 'Assistant Professor', 'uploads/faculty/udhayakumar.jpg'),
(7, 9, 'FAC_AIML_007', 1, 'Assistant Professor', 'uploads/faculty/gokilamani.jpg'),
(8, 10, 'FAC_AIML_008', 1, 'Professor', 'uploads/faculty/bhuvaneswari.jpg'),
(9, 11, 'FAC_AIML_009', 1, 'Assistant Professor', 'uploads/faculty/nagaraju.jpg');

-- 5. STUDENTS DETAILS
INSERT INTO students (id, user_id, student_id, class_id, year, section, photo_path) VALUES
(1, 12, 'AIML001', 1, 1, 'A', 'uploads/students/AIML001.jpg'),
(2, 13, 'AIML002', 1, 1, 'A', 'uploads/students/AIML002.jpg'),
(3, 14, 'AIML003', 1, 1, 'A', 'uploads/students/AIML003.jpg'),
(4, 15, 'AIML004', 1, 1, 'A', 'uploads/students/AIML004.jpg'),
(5, 16, 'AIML005', 1, 1, 'A', 'uploads/students/AIML005.jpg');

-- 6. SUBJECTS (16 Curriculum Courses)
INSERT INTO subjects (id, subject_code, subject_name, short_name, credits) VALUES
(1, 'MA3354', 'DISCRETE MATHEMATICS FOR COMPUTING', 'DM', 4),
(2, 'CS3351', 'DATA STRUCTURES AND ALGORITHMS', 'DSA', 3),
(3, 'CS3391', 'OBJECT ORIENTED PROGRAMMING USING JAVA', 'OOPS', 3),
(4, 'CS3352', 'COMPUTER ORGANIZATION AND ARCHITECTURE', 'COA', 3),
(5, 'CS3361', 'COMPUTER ORGANIZATION AND ARCHITECTURE LAB', 'COA LAB', 2),
(6, 'CS3381', 'DATA STRUCTURES LAB', 'DS LAB', 2),
(7, 'CS3382', 'JAVA PROGRAMMING LAB', 'JAVA LAB', 2),
(8, 'AD3351', 'FOUNDATIONS OF DATA SCIENCE', 'FDS', 3),
(9, 'AD3361', 'FOUNDATIONS OF DATA SCIENCE LAB', 'FDS LAB', 2),
(10, 'MC3301', 'LIFE SKILLS AND ETHICS', 'MC', 2),
(11, 'VE3301', 'VOCATIONAL ENHANCEMENT TRAINING', 'VEC', 1),
(12, 'HS3301', 'APTITUDE AND COMMUNICATION FOR ENGINEERS', 'APT/COMM', 2),
(13, 'TW3301', 'TUTOR WARD MEETING', 'TWM', 1),
(14, 'LB3301', 'LIBRARY', 'LIB', 1),
(15, 'IC3301', 'IIC ACTIVITY', 'IIC', 1),
(16, 'CS3392', 'JAVA PROGRAMMING', 'JAVA', 3);

-- 7. TIMETABLE MASTER DATA (42 SLOTS: Monday to Saturday, Hours 1 to 7)
-- Daily Schedule Timings:
-- Hour 1: 09:10:00 - 10:00:00
-- Hour 2: 10:00:00 - 10:50:00
-- Hour 3: 11:10:00 - 12:00:00
-- Hour 4: 12:00:00 - 12:50:00
-- Hour 5: 01:40:00 - 02:30:00
-- Hour 6: 02:30:00 - 03:20:00
-- Hour 7: 03:20:00 - 04:10:00

-- MONDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Monday', 1, 1, 8, 7, '09:10:00', '10:00:00'),   -- H1: FDS (Gokilamani)
('Monday', 1, 2, 2, 2, '10:00:00', '10:50:00'),   -- H2: DSA (Eshwar)
('Monday', 1, 3, 1, 1, '11:10:00', '12:00:00'),   -- H3: DM (Shobana)
('Monday', 1, 4, 10, 7, '12:00:00', '12:50:00'),  -- H4: MC (Gokilamani)
('Monday', 1, 5, 2, 2, '13:40:00', '14:30:00'),   -- H5: DSA (Eshwar)
('Monday', 1, 6, 4, 5, '14:30:00', '15:20:00'),   -- H6: COA (Jyothi Lakshmi)
('Monday', 1, 7, 12, 8, '15:20:00', '16:10:00');  -- H7: APT/COMM (Bhuvaneswari)

-- TUESDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Tuesday', 1, 1, 4, 4, '09:10:00', '10:00:00'),   -- H1: COA (Nansiyaz Banu)
('Tuesday', 1, 2, 15, 7, '10:00:00', '10:50:00'),  -- H2: IIC (Gokilamani)
('Tuesday', 1, 3, 4, 5, '11:10:00', '12:00:00'),   -- H3: COA (Jyothi Lakshmi)
('Tuesday', 1, 4, 6, 6, '12:00:00', '12:50:00'),   -- H4: DS LAB (Udhayakumar)
('Tuesday', 1, 5, 6, 6, '13:40:00', '14:30:00'),   -- H5: DS LAB (Udhayakumar)
('Tuesday', 1, 6, 6, 6, '14:30:00', '15:20:00'),   -- H6: DS LAB (Udhayakumar)
('Tuesday', 1, 7, 14, 6, '15:20:00', '16:10:00');  -- H7: LIB (Udhayakumar)

-- WEDNESDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Wednesday', 1, 1, 5, 4, '09:10:00', '10:00:00'),  -- H1: COA LAB (Nansiyaz Banu)
('Wednesday', 1, 2, 5, 5, '10:00:00', '10:50:00'),  -- H2: COA LAB (Jyothi Lakshmi)
('Wednesday', 1, 3, 1, 1, '11:10:00', '12:00:00'),  -- H3: DM (Shobana)
('Wednesday', 1, 4, 2, 2, '12:00:00', '12:50:00'),  -- H4: DSA (Eshwar)
('Wednesday', 1, 5, 8, 7, '13:40:00', '14:30:00'),  -- H5: FDS (Gokilamani)
('Wednesday', 1, 6, 12, 8, '14:30:00', '15:20:00'), -- H6: APT/COMM (Bhuvaneswari)
('Wednesday', 1, 7, 12, 7, '15:20:00', '16:10:00'); -- H7: APT/COMM (Gokilamani)

-- THURSDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Thursday', 1, 1, 2, 2, '09:10:00', '10:00:00'),  -- H1: DSA (Eshwar)
('Thursday', 1, 2, 1, 1, '10:00:00', '10:50:00'),  -- H2: DM (Shobana)
('Thursday', 1, 3, 9, 7, '11:10:00', '12:00:00'),  -- H3: FDS LAB (Gokilamani)
('Thursday', 1, 4, 9, 7, '12:00:00', '12:50:00'),  -- H4: FDS LAB (Gokilamani)
('Thursday', 1, 5, 1, 1, '13:40:00', '14:30:00'),  -- H5: DM (Shobana)
('Thursday', 1, 6, 11, 7, '14:30:00', '15:20:00'), -- H6: VEC (Gokilamani)
('Thursday', 1, 7, 11, 7, '15:20:00', '16:10:00'); -- H7: VEC (Gokilamani)

-- FRIDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Friday', 1, 1, 1, 1, '09:10:00', '10:00:00'),   -- H1: DM (Shobana)
('Friday', 1, 2, 4, 4, '10:00:00', '10:50:00'),   -- H2: COA (Nansiyaz Banu)
('Friday', 1, 3, 8, 7, '11:10:00', '12:00:00'),   -- H3: FDS (Gokilamani)
('Friday', 1, 4, 1, 1, '12:00:00', '12:50:00'),   -- H4: DM (Shobana)
('Friday', 1, 5, 14, 6, '13:40:00', '14:30:00'),  -- H5: LIB (Udhayakumar)
('Friday', 1, 6, 10, 7, '14:30:00', '15:20:00'),  -- H6: MC (Gokilamani)
('Friday', 1, 7, 13, 2, '15:20:00', '16:10:00');  -- H7: TWM (All Faculty / Eshwar)

-- SATURDAY
INSERT INTO timetable (day_of_week, class_id, hour_number, subject_id, faculty_id, start_time, end_time) VALUES
('Saturday', 1, 1, 3, 3, '09:10:00', '10:00:00'),  -- H1: OOPS (Nagaraj)
('Saturday', 1, 2, 3, 3, '10:00:00', '10:50:00'),  -- H2: OOPS (Nagaraj)
('Saturday', 1, 3, 3, 3, '11:10:00', '12:00:00'),  -- H3: OOPS (Nagaraj)
('Saturday', 1, 4, 16, 9, '12:00:00', '12:50:00'), -- H4: JAVA (Nagaraju)
('Saturday', 1, 5, 7, 9, '13:40:00', '14:30:00'),  -- H5: JAVA LAB (Nagaraju)
('Saturday', 1, 6, 7, 9, '14:30:00', '15:20:00'),  -- H6: JAVA LAB (Nagaraju)
('Saturday', 1, 7, 7, 9, '15:20:00', '16:10:00');  -- H7: JAVA LAB (Nagaraju)

-- 8. INITIAL FACE EMBEDDING PLACEHOLDERS (Normalized 128-dim Vector Arrays)
-- Synthetic enrollment vectors stored as valid JSON arrays for instant initialization
INSERT INTO face_embeddings (user_id, embedding_data, model_name, is_active) VALUES
(12, '[0.05, -0.12, 0.08, 0.22, -0.15, 0.03, 0.11, -0.09, 0.04, 0.17, -0.02, 0.09, -0.14, 0.06, 0.18, -0.05, 0.12, -0.08, 0.01, 0.14, -0.11, 0.07, 0.16, -0.03, 0.08, -0.10, 0.02, 0.15, -0.06, 0.11, -0.13, 0.05, 0.19, -0.04, 0.09, -0.07, 0.03, 0.13, -0.12, 0.08, 0.15, -0.01, 0.10, -0.09, 0.04, 0.16, -0.07, 0.12, -0.14, 0.06, 0.17, -0.03, 0.08, -0.11, 0.02, 0.14, -0.05, 0.10, -0.12, 0.04, 0.18, -0.06, 0.09, -0.08, 0.01, 0.15, -0.10, 0.07, 0.16, -0.02, 0.07, -0.09, 0.03, 0.13, -0.08, 0.11, -0.15, 0.05, 0.18, -0.04, 0.09, -0.07, 0.02, 0.14, -0.11, 0.08, 0.17, -0.01, 0.06, -0.10, 0.04, 0.15, -0.07, 0.12, -0.13, 0.06, 0.19, -0.05, 0.08, -0.08, 0.03, 0.14, -0.09, 0.11, -0.16, 0.04, 0.17, -0.02, 0.07, -0.11, 0.01, 0.13, -0.06, 0.09, -0.12, 0.05, 0.18, -0.04, 0.08, -0.07, 0.02, 0.15, -0.10, 0.06, 0.16, -0.03, 0.09, -0.08]', 'face_recognition_v1', TRUE),
(13, '[0.07, -0.10, 0.06, 0.20, -0.13, 0.05, 0.10, -0.07, 0.06, 0.15, -0.04, 0.08, -0.12, 0.08, 0.16, -0.07, 0.10, -0.06, 0.03, 0.12, -0.13, 0.05, 0.14, -0.05, 0.06, -0.12, 0.04, 0.13, -0.08, 0.09, -0.11, 0.07, 0.17, -0.06, 0.07, -0.09, 0.05, 0.11, -0.14, 0.06, 0.13, -0.03, 0.08, -0.11, 0.06, 0.14, -0.09, 0.10, -0.12, 0.08, 0.15, -0.05, 0.06, -0.13, 0.04, 0.12, -0.07, 0.08, -0.10, 0.06, 0.16, -0.08, 0.07, -0.10, 0.03, 0.13, -0.12, 0.05, 0.14, -0.04, 0.05, -0.11, 0.05, 0.11, -0.10, 0.09, -0.13, 0.07, 0.16, -0.06, 0.07, -0.09, 0.04, 0.12, -0.13, 0.06, 0.15, -0.03, 0.04, -0.12, 0.06, 0.13, -0.09, 0.10, -0.11, 0.08, 0.17, -0.07, 0.06, -0.10, 0.05, 0.12, -0.11, 0.09, -0.14, 0.06, 0.15, -0.04, 0.05, -0.13, 0.03, 0.11, -0.08, 0.07, -0.10, 0.07, 0.16, -0.06, 0.06, -0.09, 0.04, 0.13, -0.12, 0.04, 0.14, -0.05, 0.07, -0.10]', 'face_recognition_v1', TRUE);
