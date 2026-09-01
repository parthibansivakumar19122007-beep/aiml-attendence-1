-- =====================================================================================
-- AIML SMART FACE RECOGNITION ATTENDANCE MANAGEMENT SYSTEM - ALL-IN-ONE SETUP
-- =====================================================================================

CREATE DATABASE IF NOT EXISTS aiml_attendance_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE aiml_attendance_db;

SOURCE schema.sql;
SOURCE seed.sql;
