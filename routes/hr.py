from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from auth import login_required, role_required
from database import get_db_connection
from qr_utils import generate_employee_qr_code, get_employee_qr_download_path
from datetime import datetime
import os

hr_bp = Blueprint('hr', __name__)

@hr_bp.route('/add_employee', methods=['GET', 'POST'])
@login_required
@role_required('HR')
def add_employee():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        department = request.form['department']
        position = request.form['position']
        try:
            salary_rate = float(request.form['salary_rate'])
        except ValueError:
            salary_rate = 0.0
        role = request.form['role']
        nfc_id = request.form.get('nfc_id', '').strip()  # Optional NFC ID
        
        # Handle file upload
        profile_picture = ''
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                # Check file extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(file.filename)
                    # Add timestamp to filename to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_picture = filename
        
        from database import next_employee_id
        empid = next_employee_id()
        
        conn = get_db_connection()
        try:
            # Insert employee with NFC ID
            conn.execute('''INSERT INTO employees(employee_id,username,password,name,department,position,salary_rate,role,status,profile_picture,nfc_id)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                        (empid, username, password, name, department, position, salary_rate, role, 'Active', profile_picture, nfc_id))
            
            # Get the employee's database ID for QR code generation
            employee_db_id = conn.lastrowid
            
            # Generate QR code automatically
            try:
                qr_code_path = generate_employee_qr_code(empid, name, employee_db_id)
                # Update employee record with QR code path
                conn.execute('UPDATE employees SET qr_code_path = ? WHERE id = ?', (qr_code_path, employee_db_id))
                conn.commit()
                flash(f'Employee {name} created successfully with ID {empid}. QR code generated!', 'success')
            except Exception as qr_error:
                conn.commit()  # Still commit the employee creation
                flash(f'Employee {name} created with ID {empid}, but QR code generation failed: {str(qr_error)}', 'warning')
            
            return redirect(url_for('hr.list_employees'))
        except Exception as e:
            flash(f'Error creating employee: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('hr/add_employee.html')

@hr_bp.route('/dashboard')
@login_required
@role_required('HR')
def dashboard():
    conn = get_db_connection()
    
    # Get statistics
    pending_leaves = conn.execute('SELECT COUNT(*) FROM leaves WHERE status = "Pending"').fetchone()[0]
    total_employees = conn.execute('SELECT COUNT(*) FROM employees WHERE status = "Active"').fetchone()[0]
    
    conn.close()
    
    return render_template('hr/dashboard.html', 
                         pending_leaves=pending_leaves,
                         total_employees=total_employees)

@hr_bp.route('/leaves', methods=['GET', 'POST'])
@login_required
@role_required('HR')
def manage_leaves():
    conn = get_db_connection()
    
    if request.method == 'POST':
        leave_id = request.form['leave_id']
        action = request.form['action']
        
        if action in ['Approved', 'Rejected']:
            conn.execute('UPDATE leaves SET status = ? WHERE id = ?', (action, leave_id))
            conn.commit()
            flash(f'Leave request {action.lower()} successfully', 'success')
    
    # Get pending leave requests
    pending_leaves = conn.execute('''
        SELECT l.id, e.employee_id, e.name, l.type, l.duration, l.start_date, l.end_date, l.reason, l.status
        FROM leaves l JOIN employees e ON e.id = l.employee_ref
        WHERE l.status = 'Pending'
        ORDER BY l.id
    ''').fetchall()
    
    # Get all leave requests for history
    all_leaves = conn.execute('''
        SELECT l.id, e.employee_id, e.name, l.type, l.duration, l.start_date, l.end_date, l.reason, l.status
        FROM leaves l JOIN employees e ON e.id = l.employee_ref
        ORDER BY l.id DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('hr/leaves.html', pending_leaves=pending_leaves, all_leaves=all_leaves)

@hr_bp.route('/attendance_report')
@login_required
@role_required('HR')
def attendance_report():
    conn = get_db_connection()
    
    # Get attendance records
    attendance_records = conn.execute('''
        SELECT e.employee_id, e.name, a.date, a.time_in, a.time_out
        FROM attendance a JOIN employees e ON e.id = a.employee_ref
        ORDER BY a.date DESC, e.employee_id
        LIMIT 100
    ''').fetchall()
    
    conn.close()
    
    return render_template('hr/attendance_report.html', attendance_records=attendance_records)

@hr_bp.route('/payroll_report')
@login_required
@role_required('HR')
def payroll_report():
    conn = get_db_connection()
    
    # Get payroll records
    payroll_records = conn.execute('''
        SELECT e.employee_id, e.name, p.period, p.base_salary, p.overtime, p.deductions, p.bonuses, p.net_pay
        FROM payroll p JOIN employees e ON e.id = p.employee_ref
        ORDER BY p.id DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('hr/payroll_report.html', payroll_records=payroll_records)

@hr_bp.route('/employees')
@login_required
@role_required('HR')
def list_employees():
    conn = get_db_connection()
    employees = conn.execute('''
        SELECT id, employee_id, name, department, position, role, status, profile_picture, nfc_id, qr_code_path
        FROM employees ORDER BY id
    ''').fetchall()
    conn.close()
    
    return render_template('hr/list_employees.html', employees=employees)

@hr_bp.route('/download_qr/<int:employee_id>')
@login_required
@role_required('HR')
def download_qr(employee_id):
    """Download QR code for an employee"""
    conn = get_db_connection()
    employee = conn.execute('SELECT employee_id, name, qr_code_path FROM employees WHERE id = ?', 
                           (employee_id,)).fetchone()
    conn.close()
    
    if not employee or not employee['qr_code_path']:
        flash('QR code not found for this employee', 'danger')
        return redirect(url_for('hr.list_employees'))
    
    qr_file_path = get_employee_qr_download_path(employee['qr_code_path'])
    if not qr_file_path or not os.path.exists(qr_file_path):
        flash('QR code file not found', 'danger')
        return redirect(url_for('hr.list_employees'))
    
    return send_file(qr_file_path, 
                     as_attachment=True, 
                     download_name=f"{employee['employee_id']}_{employee['name']}_QR.png",
                     mimetype='image/png')

@hr_bp.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required('HR')
def edit_employee(employee_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        department = request.form['department']
        position = request.form['position']
        try:
            salary_rate = float(request.form['salary_rate'])
        except ValueError:
            salary_rate = 0.0
        status = request.form['status']
        
        # HR can only edit Employee roles, not Admin/HR roles
        role = 'Employee'
        
        # Handle file upload
        current_employee = conn.execute('SELECT profile_picture FROM employees WHERE id = ?', (employee_id,)).fetchone()
        profile_picture = current_employee['profile_picture'] if current_employee else ''
        
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                # Check file extension
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Delete old file if it exists
                    if profile_picture:
                        old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], profile_picture)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_picture = filename
        
        try:
            conn.execute('''UPDATE employees SET username=?, password=?, name=?, department=?, position=?, 
                           salary_rate=?, role=?, status=?, profile_picture=? WHERE id=? AND role != 'Admin' ''',
                        (username, password, name, department, position, salary_rate, role, status, profile_picture, employee_id))
            conn.commit()
            flash('Employee updated successfully', 'success')
            return redirect(url_for('hr.list_employees'))
        except Exception as e:
            flash(f'Error updating employee: {str(e)}', 'danger')
        finally:
            conn.close()
    
    # GET request - fetch employee data (HR can only edit non-Admin employees)
    employee = conn.execute('SELECT * FROM employees WHERE id = ? AND role != "Admin"', (employee_id,)).fetchone()
    conn.close()
    
    if not employee:
        flash('Employee not found or access denied', 'danger')
        return redirect(url_for('hr.list_employees'))
    
    return render_template('hr/edit_employee.html', employee=employee)
