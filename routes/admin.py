from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from werkzeug.utils import secure_filename
from auth import login_required, role_required
from database import get_db_connection, next_employee_id
from qr_utils import generate_employee_qr_code, get_employee_qr_download_path
from datetime import datetime
import os

admin_bp = Blueprint('admin', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@admin_bp.route('/dashboard')
@login_required
@role_required('Admin')
def dashboard():
    conn = get_db_connection()
    
    # Get statistics
    total_employees = conn.execute('SELECT COUNT(*) FROM employees WHERE status = "Active"').fetchone()[0]
    total_attendance_today = conn.execute(
        'SELECT COUNT(*) FROM attendance WHERE date = ?', 
        (datetime.now().strftime('%Y-%m-%d'),)
    ).fetchone()[0]
    pending_leaves = conn.execute('SELECT COUNT(*) FROM leaves WHERE status = "Pending"').fetchone()[0]
    
    conn.close()
    
    return render_template('admin/dashboard.html', 
                         total_employees=total_employees,
                         total_attendance_today=total_attendance_today,
                         pending_leaves=pending_leaves)

@admin_bp.route('/employees')
@login_required
@role_required('Admin')
def list_employees():
    conn = get_db_connection()
    employees = conn.execute('''
        SELECT id, employee_id, name, department, position, role, status, profile_picture, nfc_id, qr_code_path
        FROM employees ORDER BY id
    ''').fetchall()
    conn.close()
    
    return render_template('admin/list_employees.html', employees=employees)

@admin_bp.route('/download_qr/<int:employee_id>')
@login_required
@role_required('Admin')
def download_qr(employee_id):
    """Download QR code for an employee"""
    conn = get_db_connection()
    employee = conn.execute('SELECT employee_id, name, qr_code_path FROM employees WHERE id = ?', 
                           (employee_id,)).fetchone()
    conn.close()
    
    if not employee or not employee['qr_code_path']:
        flash('QR code not found for this employee', 'danger')
        return redirect(url_for('admin.list_employees'))
    
    qr_file_path = get_employee_qr_download_path(employee['qr_code_path'])
    if not qr_file_path or not os.path.exists(qr_file_path):
        flash('QR code file not found', 'danger')
        return redirect(url_for('admin.list_employees'))
    
    return send_file(qr_file_path, 
                     as_attachment=True, 
                     download_name=f"{employee['employee_id']}_{employee['name']}_QR.png",
                     mimetype='image/png')

@admin_bp.route('/add_employee', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
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
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_picture = filename
        
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
            
            return redirect(url_for('admin.list_employees'))
        except Exception as e:
            flash(f'Error creating employee: {str(e)}', 'danger')
        finally:
            conn.close()
    
    return render_template('admin/add_employee.html')

@admin_bp.route('/payroll')
@login_required
@role_required('Admin')
def payroll():
    conn = get_db_connection()
    
    # Enhanced payroll generation
    if request.args.get('generate'):
        period = datetime.now().strftime('%Y-%m')
        employees = conn.execute('SELECT * FROM employees WHERE status = "Active"').fetchall()
        
        for emp in employees:
            # Calculate actual working days based on attendance
            actual_days = conn.execute('''SELECT COUNT(*) FROM attendance 
                                        WHERE employee_ref = ? AND date LIKE ? AND time_in IS NOT NULL AND time_out IS NOT NULL''',
                                     (emp['id'], f"{period}%")).fetchone()[0]
            
            # Base salary calculation
            base_salary = emp['salary_rate'] * actual_days
            
            # Calculate overtime (hours over 8 per day)
            overtime_hours = conn.execute('''SELECT SUM(
                CASE WHEN time_in IS NOT NULL AND time_out IS NOT NULL THEN
                    MAX(0, (strftime('%s', time_out) - strftime('%s', time_in)) / 3600.0 - 8)
                ELSE 0 END
            ) FROM attendance WHERE employee_ref = ? AND date LIKE ?''', 
            (emp['id'], f"{period}%")).fetchone()[0] or 0
            
            overtime = overtime_hours * (emp['salary_rate'] / 8) * 1.5  # 1.5x rate for overtime
            
            # Calculate deductions (tax, insurance, etc.)
            gross_pay = base_salary + overtime
            tax_deduction = gross_pay * 0.12  # 12% income tax
            insurance_deduction = gross_pay * 0.03  # 3% health insurance
            retirement_deduction = gross_pay * 0.05  # 5% retirement fund
            deductions = tax_deduction + insurance_deduction + retirement_deduction
            
            # Performance bonuses (simplified - could be enhanced)
            bonuses = 0
            if actual_days >= 20:  # Full attendance bonus
                bonuses += emp['salary_rate'] * 2
            
            net_pay = gross_pay + bonuses - deductions
            
            # Check if payroll already exists for this period
            existing = conn.execute('SELECT id FROM payroll WHERE employee_ref = ? AND period = ?',
                                  (emp['id'], period)).fetchone()
            
            if not existing:
                conn.execute('''INSERT INTO payroll(employee_ref,period,base_salary,overtime,deductions,bonuses,net_pay)
                               VALUES(?,?,?,?,?,?,?)''',
                            (emp['id'], period, base_salary, overtime, deductions, bonuses, net_pay))
        
        conn.commit()
        flash(f'Enhanced payroll generated for {period} with detailed calculations', 'success')
    
    # Get payroll records
    payroll_records = conn.execute('''
        SELECT e.employee_id, e.name, p.period, p.base_salary, p.overtime, p.deductions, p.bonuses, p.net_pay
        FROM payroll p JOIN employees e ON e.id = p.employee_ref
        ORDER BY p.id DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('admin/payroll.html', payroll_records=payroll_records)

@admin_bp.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
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
        role = request.form['role']
        status = request.form['status']
        
        # Handle file upload
        current_employee = conn.execute('SELECT profile_picture FROM employees WHERE id = ?', (employee_id,)).fetchone()
        profile_picture = current_employee['profile_picture'] if current_employee else ''
        
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
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
                           salary_rate=?, role=?, status=?, profile_picture=? WHERE id=?''',
                        (username, password, name, department, position, salary_rate, role, status, profile_picture, employee_id))
            conn.commit()
            flash('Employee updated successfully', 'success')
            return redirect(url_for('admin.list_employees'))
        except Exception as e:
            flash(f'Error updating employee: {str(e)}', 'danger')
        finally:
            conn.close()
    
    # GET request - fetch employee data
    employee = conn.execute('SELECT * FROM employees WHERE id = ?', (employee_id,)).fetchone()
    conn.close()
    
    if not employee:
        flash('Employee not found', 'danger')
        return redirect(url_for('admin.list_employees'))
    
    return render_template('admin/edit_employee.html', employee=employee)

@admin_bp.route('/delete_employee/<int:employee_id>')
@login_required
@role_required('Admin')
def delete_employee(employee_id):
    conn = get_db_connection()
    
    # Get employee info before deletion
    employee = conn.execute('SELECT name, profile_picture FROM employees WHERE id = ?', (employee_id,)).fetchone()
    
    if employee:
        # Delete profile picture if it exists
        if employee['profile_picture']:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], employee['profile_picture'])
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Set status to Inactive instead of hard delete to preserve data integrity
        conn.execute('UPDATE employees SET status = "Inactive" WHERE id = ?', (employee_id,))
        conn.commit()
        flash(f'Employee {employee["name"]} has been deactivated', 'success')
    else:
        flash('Employee not found', 'danger')
    
    conn.close()
    return redirect(url_for('admin.list_employees'))
