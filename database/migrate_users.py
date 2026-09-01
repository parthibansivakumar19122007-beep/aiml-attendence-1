import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'aiml_attendance.db')

def migrate():
    print(f"Migrating database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}, skipping.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    print("Existing columns in users:", existing_cols)

    # 1. Add username if not present
    if 'username' not in existing_cols:
        print("Adding 'username' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(80)")
        conn.commit()

    # 2. Add department if not present
    if 'department' not in existing_cols:
        print("Adding 'department' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN department VARCHAR(120) DEFAULT 'CSE-AIML'")
        conn.commit()

    # 3. Add status if not present
    if 'status' not in existing_cols:
        print("Adding 'status' column...")
        cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
        conn.commit()

    # 4. Populate missing usernames based on role and IDs
    cursor.execute("SELECT id, role, email, username FROM users")
    users = cursor.fetchall()
    
    student_idx = 1
    faculty_idx = 1
    
    for uid, role, email, uname in users:
        new_uname = uname
        if not new_uname:
            if role == 'ADMIN':
                new_uname = 'admin01'
            elif role == 'HOD':
                new_uname = 'hod01'
            elif role == 'FACULTY':
                new_uname = f"faculty0{faculty_idx}" if faculty_idx < 10 else f"faculty{faculty_idx}"
                faculty_idx += 1
            elif role == 'STUDENT':
                new_uname = f"student0{student_idx}" if student_idx < 10 else f"student{student_idx}"
                student_idx += 1
            else:
                new_uname = email.split('@')[0]

        cursor.execute("""
            UPDATE users 
            SET username = ?, department = COALESCE(department, 'CSE-AIML'), status = CASE WHEN is_active = 0 THEN 'INACTIVE' ELSE 'ACTIVE' END
            WHERE id = ?
        """, (new_uname, uid))

    conn.commit()

    # Verify
    cursor.execute("SELECT id, username, role, email, department, status FROM users")
    for row in cursor.fetchall():
        print("Migrated User:", row)

    conn.close()
    print("Database migration completed successfully!")

if __name__ == '__main__':
    migrate()
