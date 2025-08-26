from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_db_connection
from datetime import datetime, date
from qr_utils import verify_qr_scan_data

kiosk_bp = Blueprint('kiosk', __name__)

@kiosk_bp.route('/punch', methods=['GET', 'POST'])
def punch():
    if request.method == 'POST':
        # Handle both manual input and scanner input
        employee_id = request.form.get('employee_id', '').strip().upper()
        scanned_data = request.form.get('scanned_data', '').strip()
        
        # Process scanned data (NFC/QR)
        if scanned_data:
            is_valid, cleaned_id = verify_qr_scan_data(scanned_data)
            if is_valid:
                employee_id = cleaned_id
            else:
                flash('Invalid scan data format', 'danger')
                return render_template('kiosk/punch.html')
        
        if not employee_id:
            flash('Employee ID is required', 'danger')
            return render_template('kiosk/punch.html')
        
        conn = get_db_connection()
        # Search by employee_id or nfc_id
        employee = conn.execute('''SELECT * FROM employees 
                                  WHERE (employee_id = ? OR nfc_id = ?) 
                                  AND status = "Active"''',
                               (employee_id, employee_id)).fetchone()
        
        if not employee:
            flash('Employee ID/NFC not found or inactive', 'danger')
            conn.close()
            return render_template('kiosk/punch.html')
        
        today = date.today().strftime('%Y-%m-%d')
        now_time = datetime.now().strftime('%H:%M:%S')
        
        # Check if there's already an attendance record for today
        attendance_record = conn.execute('''
            SELECT id, time_in, time_out FROM attendance 
            WHERE employee_ref = ? AND date = ?
        ''', (employee['id'], today)).fetchone()
        
        if not attendance_record:
            # Time-in
            conn.execute('INSERT INTO attendance(employee_ref, date, time_in) VALUES(?,?,?)',
                        (employee['id'], today, now_time))
            conn.commit()
            message = f"✅ TIME-IN recorded at {now_time}"
            message_type = "success"
        else:
            if not attendance_record['time_out']:
                # Time-out
                conn.execute('UPDATE attendance SET time_out = ? WHERE id = ?', 
                           (now_time, attendance_record['id']))
                conn.commit()
                message = f"✅ TIME-OUT recorded at {now_time}"
                message_type = "success"
            else:
                message = "ℹ️ Already timed in and out today"
                message_type = "info"
        
        conn.close()
        
        return render_template('kiosk/punch.html',
                             employee=employee,
                             message=message,
                             message_type=message_type,
                             time_in=attendance_record['time_in'] if attendance_record else now_time,
                             time_out=attendance_record['time_out'] if attendance_record and attendance_record['time_out'] else (now_time if attendance_record else None))
    
    return render_template('kiosk/punch.html')

@kiosk_bp.route('/scan_process', methods=['POST'])
def scan_process():
    """AJAX endpoint for processing NFC/QR scans automatically"""
    try:
        data = request.get_json()
        scanned_data = data.get('scanData', '').strip()
        
        # Verify scan data
        is_valid, employee_id = verify_qr_scan_data(scanned_data)
        if not is_valid:
            return jsonify({
                'success': False, 
                'message': 'Invalid scan data format'
            })
        
        conn = get_db_connection()
        # Search by employee_id or nfc_id
        employee = conn.execute('''SELECT * FROM employees 
                                  WHERE (employee_id = ? OR nfc_id = ?) 
                                  AND status = "Active"''',
                               (employee_id, scanned_data)).fetchone()
        
        if not employee:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Employee ID/NFC not found or inactive'
            })
        
        today = date.today().strftime('%Y-%m-%d')
        now_time = datetime.now().strftime('%H:%M:%S')
        
        # Check attendance record
        attendance_record = conn.execute('''
            SELECT id, time_in, time_out FROM attendance 
            WHERE employee_ref = ? AND date = ?
        ''', (employee['id'], today)).fetchone()
        
        if not attendance_record:
            # Time-in
            conn.execute('INSERT INTO attendance(employee_ref, date, time_in) VALUES(?,?,?)',
                        (employee['id'], today, now_time))
            conn.commit()
            action = "TIME-IN"
        else:
            if not attendance_record['time_out']:
                # Time-out
                conn.execute('UPDATE attendance SET time_out = ? WHERE id = ?', 
                           (now_time, attendance_record['id']))
                conn.commit()
                action = "TIME-OUT"
            else:
                conn.close()
                return jsonify({
                    'success': False,
                    'message': 'Already timed in and out today'
                })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'✅ {action} recorded at {now_time}',
            'employee': {
                'name': employee['name'],
                'employee_id': employee['employee_id'],
                'department': employee['department'],
                'position': employee['position'],
                'profile_picture': employee['profile_picture']
            },
            'action': action,
            'time': now_time
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing scan: {str(e)}'
        })
