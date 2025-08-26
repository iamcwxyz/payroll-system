import sqlite3
from datetime import datetime, date
import re
import os
import hashlib

DB_NAME = "payroll_system.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE,           -- e.g., EMP001
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        department TEXT,
        position TEXT,
        salary_rate REAL DEFAULT 0,        -- daily rate
        role TEXT CHECK(role IN ('Admin','HR','Employee')),
        status TEXT DEFAULT 'Active',
        profile_picture TEXT,              -- store file path
        nfc_id TEXT,                       -- NFC card ID for time clock access
        qr_code_path TEXT                  -- QR code image file path
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_ref INTEGER,              -- FK to employees.id
        date TEXT,                         -- YYYY-MM-DD
        time_in TEXT,                      -- HH:MM:SS
        time_out TEXT,                     -- HH:MM:SS
        FOREIGN KEY(employee_ref) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS leaves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_ref INTEGER,
        type TEXT,                         -- Sick/Vacation/Unpaid/etc.
        duration TEXT CHECK(duration IN ('Full','Half')) DEFAULT 'Full',
        start_date TEXT,
        end_date TEXT,
        reason TEXT,
        status TEXT CHECK(status IN ('Pending','Approved','Rejected')) DEFAULT 'Pending',
        FOREIGN KEY(employee_ref) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS payroll(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_ref INTEGER,
        period TEXT,                       -- e.g., Aug-2025 or 2025-08A
        base_salary REAL,
        overtime REAL,
        deductions REAL,
        bonuses REAL,
        net_pay REAL,
        FOREIGN KEY(employee_ref) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT UNIQUE,
        setting_value TEXT,
        description TEXT,
        updated_by INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(updated_by) REFERENCES employees(id)
    )''')

    # Security audit log table
    c.execute('''CREATE TABLE IF NOT EXISTS security_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        user_id INTEGER,
        ip_address TEXT,
        user_agent TEXT,
        event_description TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id TEXT UNIQUE,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        position_applied TEXT,
        resume_file TEXT,
        work_experience TEXT,
        education TEXT,
        skills TEXT,
        status TEXT DEFAULT 'Pending',
        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_by INTEGER,
        processed_date TIMESTAMP,
        notes TEXT,
        FOREIGN KEY(processed_by) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_rooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT NOT NULL,
        room_type TEXT DEFAULT 'group',    -- 'general', 'group', 'applicant'
        join_code TEXT UNIQUE,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(created_by) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        sender_id INTEGER,
        sender_type TEXT DEFAULT 'employee',  -- 'employee' or 'applicant'
        message TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(room_id) REFERENCES chat_rooms(id),
        FOREIGN KEY(sender_id) REFERENCES employees(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS room_memberships(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        member_id INTEGER,
        member_type TEXT DEFAULT 'employee',  -- 'employee' or 'applicant'
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(room_id) REFERENCES chat_rooms(id),
        FOREIGN KEY(member_id) REFERENCES employees(id)
    )''')
    
    conn.commit()
    
    # Ensure columns exist
    ensure_columns(conn)
    conn.close()

def ensure_columns(conn):
    def has_col(table, col):
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        return any(r[1] == col for r in c.fetchall())
    
    c = conn.cursor()
    # employees: add columns if missing
    if not has_col('employees', 'employee_id'):
        c.execute("ALTER TABLE employees ADD COLUMN employee_id TEXT")
    if not has_col('employees', 'profile_picture'):
        c.execute("ALTER TABLE employees ADD COLUMN profile_picture TEXT")
    if not has_col('employees', 'status'):
        c.execute("ALTER TABLE employees ADD COLUMN status TEXT DEFAULT 'Active'")
    if not has_col('employees', 'salary_rate'):
        c.execute("ALTER TABLE employees ADD COLUMN salary_rate REAL DEFAULT 0")
    if not has_col('employees', 'role'):
        c.execute("ALTER TABLE employees ADD COLUMN role TEXT")
    if not has_col('employees', 'nfc_id'):
        c.execute("ALTER TABLE employees ADD COLUMN nfc_id TEXT")
    if not has_col('employees', 'qr_code_path'):
        c.execute("ALTER TABLE employees ADD COLUMN qr_code_path TEXT")
    
    # room_memberships: add last_read_at if missing
    if not has_col('room_memberships', 'last_read_at'):
        c.execute("ALTER TABLE room_memberships ADD COLUMN last_read_at TIMESTAMP DEFAULT '1970-01-01 00:00:00'")
        # Update existing rows to current timestamp
        c.execute("UPDATE room_memberships SET last_read_at = CURRENT_TIMESTAMP WHERE last_read_at = '1970-01-01 00:00:00'")
    
    conn.commit()

def init_default_settings():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if settings already exist
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        # Insert default settings
        default_settings = [
            ('office_hours_per_day', '8', 'Standard daily work hours for payroll calculation'),
            ('overtime_multiplier', '1.5', 'Overtime pay multiplier (e.g., 1.5 = time and a half)'),
            ('tax_rate', '0.12', 'Standard tax deduction rate'),
            ('insurance_deduction', '500', 'Monthly insurance deduction amount'),
            ('company_name', 'Federal Agency', 'Company name for reports and documents'),
            ('payroll_period', 'monthly', 'Payroll generation period (monthly/biweekly)')
        ]
        
        for setting in default_settings:
            c.execute("INSERT INTO settings (setting_name, setting_value, description) VALUES (?, ?, ?)", setting)
    
    # Create default general chat room if it doesn't exist
    c.execute("SELECT COUNT(*) FROM chat_rooms WHERE room_type = 'general'")
    if c.fetchone()[0] == 0:
        join_code = generate_join_code()
        c.execute("""INSERT INTO chat_rooms (room_name, room_type, join_code, created_by) 
                     VALUES ('General Discussion', 'general', ?, 1)""", (join_code,))
        room_id = c.lastrowid
        
        # Add all employees to general room
        c.execute("SELECT id FROM employees WHERE status = 'Active'")
        employees = c.fetchall()
        for emp in employees:
            c.execute("INSERT INTO room_memberships (room_id, member_id, member_type) VALUES (?, ?, 'employee')", 
                     (room_id, emp['id']))
    
    conn.commit()
    conn.close()

def generate_join_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_application_id():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT application_id FROM applications WHERE application_id IS NOT NULL")
    ids = [row[0] for row in c.fetchall() if row[0]]
    max_n = 0
    for s in ids:
        m = re.match(r"APP(\d{4,})$", s)
        if m:
            max_n = max(max_n, int(m.group(1)))
    conn.close()
    return f"APP{max_n+1:04d}"

def next_employee_id():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT employee_id FROM employees WHERE employee_id IS NOT NULL")
    ids = [row[0] for row in c.fetchall() if row[0]]
    max_n = 0
    for s in ids:
        m = re.match(r"EMP(\d{3,})$", s)
        if m:
            max_n = max(max_n, int(m.group(1)))
    conn.close()
    return f"EMP{max_n+1:03d}"

def ensure_admin_exists():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM employees WHERE role='Admin' LIMIT 1")
    if not c.fetchone():
        # Create default admin with hashed password
        empid = next_employee_id()
        hashed_password = hash_password('admin123')
        c.execute('''INSERT INTO employees(employee_id,username,password,name,department,position,salary_rate,role,status,profile_picture)
                     VALUES(?,?,?,?,?,?,?,?,?,?)''',
                  (empid, 'admin', hashed_password, 'System Administrator', 'IT', 'Administrator', 0, 'Admin', 'Active', ''))
        conn.commit()
        print(f"✅ Default admin created. Username: admin, Password: admin123, EMP ID: {empid}")
    conn.close()

def migrate_plain_text_passwords():
    """Convert any remaining plain text passwords to hashed versions"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, password FROM employees")
    users = c.fetchall()
    
    for user in users:
        user_id, password = user
        # Check if password is already hashed (bcrypt hashes start with $2b$)
        if not password.startswith('$2b$'):
            hashed_password = hash_password(password)
            c.execute("UPDATE employees SET password = ? WHERE id = ?", 
                     (hashed_password, user_id))
            print(f"✅ Migrated password for user ID: {user_id}")
    
    conn.commit()
    conn.close()

def log_security_event(event_type, user_id, ip_address, description, user_agent=None):
    """Log security events for audit trail"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO security_logs (event_type, user_id, ip_address, user_agent, event_description)
                 VALUES (?, ?, ?, ?, ?)''',
              (event_type, user_id, ip_address, user_agent, description))
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using bcrypt"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Initialize database
create_tables()
ensure_admin_exists()
migrate_plain_text_passwords()
init_default_settings()

def sanitize_input(input_text):
    """Sanitize user input to prevent XSS"""
    import bleach
    if input_text is None:
        return None
    return bleach.clean(str(input_text), tags=[], attributes={}, strip=True)

def validate_file_upload(file, allowed_extensions, max_size_mb=16):
    """Validate file upload security"""
    if not file or file.filename == '':
        return False, "No file selected"
    
    # Check file extension
    if '.' not in file.filename:
        return False, "Invalid file format"
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > max_size_mb * 1024 * 1024:
        return False, f"File too large. Maximum size: {max_size_mb}MB"
    
    # Check for suspicious file content
    suspicious_patterns = [b'<?php', b'<script', b'javascript:', b'vbscript:']
    file_content = file.read(1024)  # Read first 1KB
    file.seek(0)
    
    for pattern in suspicious_patterns:
        if pattern in file_content.lower():
            return False, "File contains potentially malicious content"
    
    return True, "Valid file"
