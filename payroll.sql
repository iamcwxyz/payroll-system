-- ============================================
-- Federal Payroll & Attendance System Database
-- Compatible with XAMPP/phpMyAdmin (MySQL)
-- ============================================

-- Create Database
CREATE DATABASE IF NOT EXISTS payroll_system;
USE payroll_system;

-- ============================================
-- Table: employees
-- ============================================
CREATE TABLE employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    position VARCHAR(100),
    salary_rate DECIMAL(10,2) DEFAULT 0.00,
    role ENUM('Admin', 'HR', 'Employee') DEFAULT 'Employee',
    status ENUM('Active', 'Inactive', 'Terminated') DEFAULT 'Active',
    profile_picture VARCHAR(255),
    date_hired DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================
-- Table: attendance
-- ============================================
CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    date DATE NOT NULL,
    time_in TIME,
    time_out TIME,
    hours_worked DECIMAL(4,2) DEFAULT 0.00,
    overtime_hours DECIMAL(4,2) DEFAULT 0.00,
    status ENUM('Present', 'Absent', 'Late', 'Half-day') DEFAULT 'Present',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_employee_date (employee_id, date)
);

-- ============================================
-- Table: leaves
-- ============================================
CREATE TABLE leaves (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    leave_type ENUM('Sick', 'Vacation', 'Personal', 'Emergency', 'Maternity', 'Paternity') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_requested INT NOT NULL,
    reason TEXT,
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    approved_by INT,
    approved_date TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES employees(id)
);

-- ============================================
-- Table: payroll
-- ============================================
CREATE TABLE payroll (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    days_worked INT DEFAULT 0,
    regular_hours DECIMAL(6,2) DEFAULT 0.00,
    overtime_hours DECIMAL(6,2) DEFAULT 0.00,
    gross_pay DECIMAL(10,2) DEFAULT 0.00,
    deductions DECIMAL(10,2) DEFAULT 0.00,
    net_pay DECIMAL(10,2) DEFAULT 0.00,
    sss_contribution DECIMAL(8,2) DEFAULT 0.00,
    philhealth_contribution DECIMAL(8,2) DEFAULT 0.00,
    pagibig_contribution DECIMAL(8,2) DEFAULT 0.00,
    tax_withheld DECIMAL(8,2) DEFAULT 0.00,
    status ENUM('Draft', 'Processed', 'Paid') DEFAULT 'Draft',
    generated_by INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by) REFERENCES employees(id)
);

-- ============================================
-- Table: applications
-- ============================================
CREATE TABLE applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    position_applied VARCHAR(100),
    resume_file VARCHAR(255),
    work_experience TEXT,
    education TEXT,
    skills TEXT,
    status ENUM('Pending', 'Under Review', 'Approved', 'Rejected') DEFAULT 'Pending',
    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_by INT,
    processed_date TIMESTAMP NULL,
    notes TEXT,
    FOREIGN KEY (processed_by) REFERENCES employees(id)
);

-- ============================================
-- Table: chat_rooms
-- ============================================
CREATE TABLE chat_rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_name VARCHAR(100) NOT NULL,
    room_type ENUM('general', 'group', 'direct', 'applicant') DEFAULT 'group',
    join_code VARCHAR(10) UNIQUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active TINYINT(1) DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES employees(id)
);

-- ============================================
-- Table: chat_messages
-- ============================================
CREATE TABLE chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    sender_id INT NOT NULL,
    sender_type ENUM('employee', 'applicant') DEFAULT 'employee',
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- ============================================
-- Table: room_memberships
-- ============================================
CREATE TABLE room_memberships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id INT NOT NULL,
    member_id INT NOT NULL,
    member_type ENUM('employee', 'applicant') DEFAULT 'employee',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES employees(id) ON DELETE CASCADE,
    UNIQUE KEY unique_membership (room_id, member_id, member_type)
);

-- ============================================
-- Table: settings
-- ============================================
CREATE TABLE settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES employees(id)
);

-- ============================================
-- Initial Data Inserts
-- ============================================

-- Default Admin User
INSERT INTO employees (employee_id, username, password, name, department, position, salary_rate, role, status) VALUES
('EMP001', 'admin', 'admin123', 'System Administrator', 'IT', 'System Administrator', 80000.00, 'Admin', 'Active');

-- Default HR User
INSERT INTO employees (employee_id, username, password, name, department, position, salary_rate, role, status) VALUES
('EMP002', 'hr', 'hr123', 'HR Manager', 'HR', 'Human Resources Manager', 60000.00, 'HR', 'Active');

-- Sample Employee
INSERT INTO employees (employee_id, username, password, name, department, position, salary_rate, role, status) VALUES
('EMP003', 'employee', 'emp123', 'John Doe', 'Operations', 'Operations Specialist', 35000.00, 'Employee', 'Active');

-- Default Settings
INSERT INTO settings (setting_name, setting_value, description, updated_by) VALUES
('overtime_multiplier', '1.5', 'Overtime pay multiplier', 1),
('sss_rate', '0.045', 'SSS contribution rate (4.5%)', 1),
('philhealth_rate', '0.015', 'PhilHealth contribution rate (1.5%)', 1),
('pagibig_rate', '0.02', 'Pag-IBIG contribution rate (2%)', 1),
('tax_rate', '0.12', 'Income tax rate (12%)', 1),
('standard_hours', '8', 'Standard working hours per day', 1),
('company_name', 'Federal Payroll System', 'Company name for reports', 1),
('company_address', 'Department of Human Resources, Federal Building', 'Company address', 1);

-- General Chat Room
INSERT INTO chat_rooms (room_name, room_type, join_code, created_by) VALUES
('General Discussion', 'general', 'GENERAL', 1);

-- Add all employees to general chat
INSERT INTO room_memberships (room_id, member_id, member_type) VALUES
(1, 1, 'employee'),
(1, 2, 'employee'),
(1, 3, 'employee');

-- ============================================
-- Indexes for Performance
-- ============================================
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, date);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_leaves_employee ON leaves(employee_id);
CREATE INDEX idx_leaves_status ON leaves(status);
CREATE INDEX idx_payroll_employee ON payroll(employee_id);
CREATE INDEX idx_payroll_period ON payroll(pay_period_start, pay_period_end);
CREATE INDEX idx_chat_messages_room ON chat_messages(room_id);
CREATE INDEX idx_chat_messages_sender ON chat_messages(sender_id);
CREATE INDEX idx_room_memberships_room ON room_memberships(room_id);
CREATE INDEX idx_room_memberships_member ON room_memberships(member_id);
CREATE INDEX idx_applications_status ON applications(status);

-- ============================================
-- Views for Common Queries
-- ============================================

-- Employee Summary View
CREATE VIEW employee_summary AS
SELECT 
    e.id,
    e.employee_id,
    e.name,
    e.department,
    e.position,
    e.salary_rate,
    e.role,
    e.status,
    COUNT(DISTINCT a.id) as total_attendance_records,
    COUNT(DISTINCT l.id) as total_leave_requests,
    COUNT(DISTINCT p.id) as total_payroll_records
FROM employees e
LEFT JOIN attendance a ON e.id = a.employee_id
LEFT JOIN leaves l ON e.id = l.employee_id
LEFT JOIN payroll p ON e.id = p.employee_id
GROUP BY e.id;

-- Monthly Payroll Summary View
CREATE VIEW monthly_payroll_summary AS
SELECT 
    YEAR(pay_period_start) as payroll_year,
    MONTH(pay_period_start) as payroll_month,
    COUNT(*) as total_employees,
    SUM(gross_pay) as total_gross_pay,
    SUM(deductions) as total_deductions,
    SUM(net_pay) as total_net_pay,
    AVG(regular_hours) as avg_regular_hours,
    SUM(overtime_hours) as total_overtime_hours
FROM payroll
WHERE status = 'Processed'
GROUP BY YEAR(pay_period_start), MONTH(pay_period_start)
ORDER BY payroll_year DESC, payroll_month DESC;

-- ============================================
-- Stored Procedures (Optional)
-- ============================================

DELIMITER //

-- Calculate Employee Payroll
CREATE PROCEDURE CalculateEmployeePayroll(
    IN emp_id INT,
    IN period_start DATE,
    IN period_end DATE
)
BEGIN
    DECLARE total_hours DECIMAL(6,2) DEFAULT 0;
    DECLARE regular_hrs DECIMAL(6,2) DEFAULT 0;
    DECLARE overtime_hrs DECIMAL(6,2) DEFAULT 0;
    DECLARE daily_rate DECIMAL(10,2) DEFAULT 0;
    DECLARE gross DECIMAL(10,2) DEFAULT 0;
    DECLARE sss_deduction DECIMAL(8,2) DEFAULT 0;
    DECLARE philhealth_deduction DECIMAL(8,2) DEFAULT 0;
    DECLARE pagibig_deduction DECIMAL(8,2) DEFAULT 0;
    DECLARE tax_deduction DECIMAL(8,2) DEFAULT 0;
    DECLARE total_deductions DECIMAL(10,2) DEFAULT 0;
    DECLARE net DECIMAL(10,2) DEFAULT 0;
    
    -- Get employee salary rate
    SELECT salary_rate INTO daily_rate FROM employees WHERE id = emp_id;
    
    -- Calculate total hours worked in period
    SELECT 
        SUM(hours_worked),
        SUM(CASE WHEN hours_worked <= 8 THEN hours_worked ELSE 8 END),
        SUM(CASE WHEN hours_worked > 8 THEN hours_worked - 8 ELSE 0 END)
    INTO total_hours, regular_hrs, overtime_hrs
    FROM attendance 
    WHERE employee_id = emp_id 
    AND date BETWEEN period_start AND period_end;
    
    -- Calculate gross pay
    SET gross = (regular_hrs * daily_rate) + (overtime_hrs * daily_rate * 1.5);
    
    -- Calculate deductions
    SET sss_deduction = gross * 0.045;
    SET philhealth_deduction = gross * 0.015;
    SET pagibig_deduction = gross * 0.02;
    SET tax_deduction = gross * 0.12;
    SET total_deductions = sss_deduction + philhealth_deduction + pagibig_deduction + tax_deduction;
    SET net = gross - total_deductions;
    
    -- Insert or update payroll record
    INSERT INTO payroll (
        employee_id, pay_period_start, pay_period_end,
        regular_hours, overtime_hours, gross_pay, deductions, net_pay,
        sss_contribution, philhealth_contribution, pagibig_contribution, tax_withheld,
        status, generated_by, generated_at
    ) VALUES (
        emp_id, period_start, period_end,
        regular_hrs, overtime_hrs, gross, total_deductions, net,
        sss_deduction, philhealth_deduction, pagibig_deduction, tax_deduction,
        'Processed', 1, NOW()
    ) ON DUPLICATE KEY UPDATE
        regular_hours = VALUES(regular_hours),
        overtime_hours = VALUES(overtime_hours),
        gross_pay = VALUES(gross_pay),
        deductions = VALUES(deductions),
        net_pay = VALUES(net_pay),
        sss_contribution = VALUES(sss_contribution),
        philhealth_contribution = VALUES(philhealth_contribution),
        pagibig_contribution = VALUES(pagibig_contribution),
        tax_withheld = VALUES(tax_withheld),
        generated_at = NOW();
        
END //

DELIMITER ;

-- ============================================
-- Sample Data for Testing
-- ============================================

-- Additional Sample Employees
INSERT INTO employees (employee_id, username, password, name, department, position, salary_rate, role, status) VALUES
('EMP004', 'jane.smith', 'jane123', 'Jane Smith', 'Finance', 'Financial Analyst', 45000.00, 'Employee', 'Active'),
('EMP005', 'mike.johnson', 'mike123', 'Mike Johnson', 'IT', 'Software Developer', 55000.00, 'Employee', 'Active'),
('EMP006', 'sarah.williams', 'sarah123', 'Sarah Williams', 'HR', 'HR Specialist', 40000.00, 'HR', 'Active');

-- Sample Attendance Records
INSERT INTO attendance (employee_id, date, time_in, time_out, hours_worked, status) VALUES
(3, '2025-08-20', '08:00:00', '17:00:00', 8.00, 'Present'),
(3, '2025-08-21', '08:15:00', '17:00:00', 7.75, 'Late'),
(3, '2025-08-22', '08:00:00', '18:00:00', 9.00, 'Present'),
(4, '2025-08-20', '09:00:00', '18:00:00', 8.00, 'Present'),
(4, '2025-08-21', '09:00:00', '18:00:00', 8.00, 'Present'),
(5, '2025-08-20', '08:30:00', '17:30:00', 8.00, 'Present'),
(5, '2025-08-21', '08:30:00', '19:00:00', 9.50, 'Present');

-- Sample Leave Requests
INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days_requested, reason, status, approved_by) VALUES
(3, 'Sick', '2025-08-25', '2025-08-25', 1, 'Medical appointment', 'Approved', 2),
(4, 'Vacation', '2025-09-01', '2025-09-05', 5, 'Family vacation', 'Pending', NULL),
(5, 'Personal', '2025-08-30', '2025-08-30', 1, 'Personal matters', 'Approved', 6);

-- Sample Applications
INSERT INTO applications (application_id, full_name, email, phone, position_applied, work_experience, education, skills, status) VALUES
('APP001', 'Robert Brown', 'robert.brown@email.com', '+63-912-345-6789', 'Marketing Specialist', '3 years in digital marketing', 'Bachelor of Marketing', 'Social Media, Analytics, Content Creation', 'Under Review'),
('APP002', 'Lisa Garcia', 'lisa.garcia@email.com', '+63-998-765-4321', 'Accountant', '5 years in accounting', 'CPA, Bachelor of Accountancy', 'Financial Reporting, Tax Preparation, Auditing', 'Pending'),
('APP003', 'David Lee', 'david.lee@email.com', '+63-917-555-0123', 'Security Officer', '2 years in security', 'Security Management Certificate', 'Physical Security, CCTV Operations, Access Control', 'Approved');

-- ============================================
-- Database Functions and Triggers
-- ============================================

-- Trigger to auto-calculate hours worked
DELIMITER //

CREATE TRIGGER calculate_hours_worked
BEFORE INSERT ON attendance
FOR EACH ROW
BEGIN
    IF NEW.time_in IS NOT NULL AND NEW.time_out IS NOT NULL THEN
        SET NEW.hours_worked = TIMESTAMPDIFF(MINUTE, 
            CONCAT(NEW.date, ' ', NEW.time_in), 
            CONCAT(NEW.date, ' ', NEW.time_out)
        ) / 60.0;
        
        IF NEW.hours_worked > 8 THEN
            SET NEW.overtime_hours = NEW.hours_worked - 8;
        ELSE 
            SET NEW.overtime_hours = 0;
        END IF;
    END IF;
END //

CREATE TRIGGER calculate_hours_worked_update
BEFORE UPDATE ON attendance
FOR EACH ROW
BEGIN
    IF NEW.time_in IS NOT NULL AND NEW.time_out IS NOT NULL THEN
        SET NEW.hours_worked = TIMESTAMPDIFF(MINUTE, 
            CONCAT(NEW.date, ' ', NEW.time_in), 
            CONCAT(NEW.date, ' ', NEW.time_out)
        ) / 60.0;
        
        IF NEW.hours_worked > 8 THEN
            SET NEW.overtime_hours = NEW.hours_worked - 8;
        ELSE 
            SET NEW.overtime_hours = 0;
        END IF;
    END IF;
END //

DELIMITER ;

-- ============================================
-- Useful Queries for Reports
-- ============================================

-- Daily Attendance Report
-- SELECT e.employee_id, e.name, a.date, a.time_in, a.time_out, a.hours_worked, a.status
-- FROM employees e
-- LEFT JOIN attendance a ON e.id = a.employee_id
-- WHERE a.date = CURDATE()
-- ORDER BY e.employee_id;

-- Monthly Payroll Report
-- SELECT e.employee_id, e.name, p.pay_period_start, p.pay_period_end, 
--        p.regular_hours, p.overtime_hours, p.gross_pay, p.deductions, p.net_pay
-- FROM employees e
-- JOIN payroll p ON e.id = p.employee_id
-- WHERE YEAR(p.pay_period_start) = YEAR(CURDATE()) 
-- AND MONTH(p.pay_period_start) = MONTH(CURDATE())
-- ORDER BY e.employee_id;

-- Leave Summary Report
-- SELECT e.employee_id, e.name, 
--        COUNT(CASE WHEN l.status = 'Approved' THEN 1 END) as approved_leaves,
--        SUM(CASE WHEN l.status = 'Approved' THEN l.days_requested ELSE 0 END) as total_leave_days
-- FROM employees e
-- LEFT JOIN leaves l ON e.id = l.employee_id
-- WHERE YEAR(l.start_date) = YEAR(CURDATE())
-- GROUP BY e.id
-- ORDER BY e.employee_id;

-- ============================================
-- Admin User Accounts
-- ============================================
-- Default Login Credentials:
-- Admin: username=admin, password=admin123
-- HR: username=hr, password=hr123  
-- Employee: username=employee, password=emp123
-- ============================================