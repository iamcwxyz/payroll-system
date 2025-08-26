from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth import login_required, role_required
from database import get_db_connection

employee_bp = Blueprint('employee', __name__)

@employee_bp.route('/dashboard')
@login_required
@role_required('Employee')
def dashboard():
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Get employee's recent attendance
    recent_attendance = conn.execute('''
        SELECT date, time_in, time_out FROM attendance 
        WHERE employee_ref = ? 
        ORDER BY date DESC LIMIT 5
    ''', (user_id,)).fetchall()
    
    # Get employee's leave balance (simplified)
    total_leaves = conn.execute('SELECT COUNT(*) FROM leaves WHERE employee_ref = ?', (user_id,)).fetchone()[0]
    approved_leaves = conn.execute('SELECT COUNT(*) FROM leaves WHERE employee_ref = ? AND status = "Approved"', (user_id,)).fetchone()[0]
    pending_leaves = conn.execute('SELECT COUNT(*) FROM leaves WHERE employee_ref = ? AND status = "Pending"', (user_id,)).fetchone()[0]
    
    conn.close()
    
    return render_template('employee/dashboard.html',
                         recent_attendance=recent_attendance,
                         total_leaves=total_leaves,
                         approved_leaves=approved_leaves,
                         pending_leaves=pending_leaves)

@employee_bp.route('/request_leave', methods=['GET', 'POST'])
@login_required
@role_required('Employee')
def request_leave():
    if request.method == 'POST':
        user_id = session['user_id']
        leave_type = request.form['type']
        duration = request.form['duration']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        reason = request.form['reason']
        
        conn = get_db_connection()
        conn.execute('''INSERT INTO leaves(employee_ref,type,duration,start_date,end_date,reason,status)
                       VALUES(?,?,?,?,?,?,'Pending')''',
                    (user_id, leave_type, duration, start_date, end_date, reason))
        conn.commit()
        conn.close()
        
        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('employee.dashboard'))
    
    return render_template('employee/request_leave.html')

@employee_bp.route('/stats')
@login_required
@role_required('Employee')
def stats():
    user_id = session['user_id']
    conn = get_db_connection()
    
    # Get attendance records
    attendance_records = conn.execute('''
        SELECT date, time_in, time_out FROM attendance 
        WHERE employee_ref = ? 
        ORDER BY date DESC
    ''', (user_id,)).fetchall()
    
    # Get leave records
    leave_records = conn.execute('''
        SELECT type, duration, start_date, end_date, status 
        FROM leaves 
        WHERE employee_ref = ? 
        ORDER BY id DESC
    ''', (user_id,)).fetchall()
    
    # Get payroll records
    payroll_records = conn.execute('''
        SELECT period, base_salary, overtime, deductions, bonuses, net_pay 
        FROM payroll 
        WHERE employee_ref = ? 
        ORDER BY id DESC
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return render_template('employee/stats.html',
                         attendance_records=attendance_records,
                         leave_records=leave_records,
                         payroll_records=payroll_records)
