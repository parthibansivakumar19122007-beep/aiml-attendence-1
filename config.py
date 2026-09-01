import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'aiml-smart-attendance-secret-key-2026')
    
    # Database Configuration
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'aiml_attendance_db')

    # MySQL connection string
    MYSQL_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    
    # Database URI priority:
    # 1. DATABASE_URL from .env
    # 2. SQLite if USE_SQLITE is set to '1' (Default for local standalone execution)
    # 3. MySQL URI
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    elif os.environ.get('USE_SQLITE', '1') == '1':
        SQLALCHEMY_DATABASE_URI = 'sqlite:///aiml_attendance.db'
    else:
        SQLALCHEMY_DATABASE_URI = MYSQL_URI

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Configuration
    SESSION_COOKIE_NAME = 'aiml_attendance_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # Institutional Timezone (Indian Standard Time)
    TIMEZONE = 'Asia/Kolkata'
    
    # Institution Info
    COLLEGE_NAME = "Nehru Institute of Technology (Autonomous)"
    DEPARTMENT_NAME = "CSE – Artificial Intelligence and Machine Learning"
    CLASS_NAME = "I B.E II AIML"
    ACADEMIC_YEAR = "2026–2027"
    TIMETABLE_EFFECTIVE_FROM = "17-06-2026"
    
    # Geofence Security Radius (in meters)
    DEFAULT_GEOFENCE_RADIUS_METERS = float(os.environ.get('GEOFENCE_RADIUS_M', 50.0))
