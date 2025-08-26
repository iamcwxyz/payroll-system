"""
Security management routes
Admin-only security dashboard and configuration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, role_required
from database import get_db_connection, log_security_event
from backup_system import backup_manager
from datetime import datetime, timedelta

security_bp = Blueprint('security', __name__)

@security_bp.route('/security/dashboard')
@login_required
@role_required('Admin')
def dashboard():
    """Security dashboard with system status and logs"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get recent security events
    c.execute("""
        SELECT sl.*, e.name as user_name
        FROM security_logs sl
        LEFT JOIN employees e ON sl.user_id = e.id
        ORDER BY sl.timestamp DESC
        LIMIT 50
    """)
    security_logs = c.fetchall()
    
    # Get security statistics
    c.execute("""
        SELECT 
            COUNT(CASE WHEN event_type = 'LOGIN_SUCCESS' AND timestamp > datetime('now', '-24 hours') THEN 1 END) as logins_24h,
            COUNT(CASE WHEN event_type = 'LOGIN_FAILED' AND timestamp > datetime('now', '-24 hours') THEN 1 END) as failed_logins_24h,
            COUNT(CASE WHEN event_type = 'SESSION_TIMEOUT' AND timestamp > datetime('now', '-24 hours') THEN 1 END) as timeouts_24h,
            COUNT(CASE WHEN timestamp > datetime('now', '-7 days') THEN 1 END) as total_events_7d
        FROM security_logs
    """)
    stats = c.fetchone()
    
    # Get active sessions count
    c.execute("SELECT COUNT(*) FROM employees WHERE status = 'Active'")
    total_users = c.fetchone()[0]
    
    conn.close()
    
    # Get backup information
    backups = backup_manager.list_backups()
    latest_backup = backups[0] if backups else None
    
    return render_template('admin/security_dashboard.html', 
                         security_logs=security_logs, 
                         stats=stats,
                         total_users=total_users,
                         backups=backups[:5],  # Show 5 most recent
                         latest_backup=latest_backup)

@security_bp.route('/security/backup/create', methods=['POST'])
@login_required
@role_required('Admin')
def create_backup():
    """Create manual database backup"""
    try:
        success, result = backup_manager.create_full_backup(compress=True)
        
        if success:
            log_security_event('MANUAL_BACKUP', session['user_id'], request.remote_addr, 
                             f"Manual backup created by {session['name']}")
            flash('Database backup created successfully', 'success')
        else:
            flash(f'Backup failed: {result}', 'danger')
            
    except Exception as e:
        flash(f'Backup error: {str(e)}', 'danger')
    
    return redirect(url_for('security.dashboard'))

@security_bp.route('/security/backup/restore', methods=['POST'])
@login_required
@role_required('Admin')
def restore_backup():
    """Restore database from backup"""
    backup_name = request.form.get('backup_name')
    
    if not backup_name:
        flash('No backup selected', 'danger')
        return redirect(url_for('security.dashboard'))
    
    try:
        backups = backup_manager.list_backups()
        backup_to_restore = None
        
        for backup in backups:
            if backup['backup_name'] == backup_name:
                backup_to_restore = backup
                break
        
        if not backup_to_restore:
            flash('Backup not found', 'danger')
            return redirect(url_for('security.dashboard'))
        
        # Verify backup integrity first
        success, message = backup_manager.verify_backup_integrity(backup_to_restore['backup_path'])
        if not success:
            flash(f'Backup integrity check failed: {message}', 'danger')
            return redirect(url_for('security.dashboard'))
        
        # Restore backup
        success, result = backup_manager.restore_backup(backup_to_restore['backup_path'], session['user_id'])
        
        if success:
            log_security_event('DATABASE_RESTORE', session['user_id'], request.remote_addr, 
                             f"Database restored from {backup_name} by {session['name']}")
            flash('Database restored successfully. Please restart the application.', 'warning')
        else:
            flash(f'Restore failed: {result}', 'danger')
            
    except Exception as e:
        flash(f'Restore error: {str(e)}', 'danger')
    
    return redirect(url_for('security.dashboard'))

@security_bp.route('/security/logs/clear', methods=['POST'])
@login_required
@role_required('Admin')
def clear_security_logs():
    """Clear old security logs (keep last 1000 entries)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Keep only the most recent 1000 entries
        c.execute("""
            DELETE FROM security_logs 
            WHERE id NOT IN (
                SELECT id FROM security_logs 
                ORDER BY timestamp DESC 
                LIMIT 1000
            )
        """)
        
        deleted_count = c.rowcount
        conn.commit()
        conn.close()
        
        log_security_event('SECURITY_LOGS_CLEARED', session['user_id'], request.remote_addr, 
                         f"Cleared {deleted_count} old security log entries")
        
        flash(f'Cleared {deleted_count} old security log entries', 'info')
        
    except Exception as e:
        flash(f'Error clearing logs: {str(e)}', 'danger')
    
    return redirect(url_for('security.dashboard'))

@security_bp.route('/security/api/stats')
@login_required
@role_required('Admin')
def api_security_stats():
    """API endpoint for security statistics (for charts)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get hourly login statistics for the last 24 hours
        c.execute("""
            SELECT 
                strftime('%H', timestamp) as hour,
                COUNT(CASE WHEN event_type = 'LOGIN_SUCCESS' THEN 1 END) as successful_logins,
                COUNT(CASE WHEN event_type = 'LOGIN_FAILED' THEN 1 END) as failed_logins
            FROM security_logs
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        """)
        hourly_stats = c.fetchall()
        
        # Get event type distribution
        c.execute("""
            SELECT event_type, COUNT(*) as count
            FROM security_logs
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY event_type
            ORDER BY count DESC
        """)
        event_types = c.fetchall()
        
        conn.close()
        
        return jsonify({
            'hourly_stats': [dict(row) for row in hourly_stats],
            'event_types': [dict(row) for row in event_types]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@security_bp.route('/security/system/status')
@login_required
@role_required('Admin')
def system_status():
    """System health and security status"""
    try:
        import psutil
        import os
        
        # Get system information
        system_info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime': datetime.now() - datetime.fromtimestamp(psutil.boot_time())
        }
        
        # Database size
        db_size = os.path.getsize('payroll_system.db') / (1024 * 1024)  # MB
        
        # Check for security issues
        security_alerts = []
        
        # Check for multiple failed login attempts
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT ip_address, COUNT(*) as failed_attempts
            FROM security_logs
            WHERE event_type = 'LOGIN_FAILED' 
            AND timestamp > datetime('now', '-1 hour')
            GROUP BY ip_address
            HAVING failed_attempts >= 5
        """)
        suspicious_ips = c.fetchall()
        
        if suspicious_ips:
            security_alerts.append({
                'level': 'warning',
                'message': f'{len(suspicious_ips)} IP addresses with multiple failed login attempts'
            })
        
        # Check backup age
        backups = backup_manager.list_backups()
        if backups:
            latest_backup_time = datetime.fromisoformat(backups[0]['backup_time'])
            backup_age = datetime.now() - latest_backup_time
            
            if backup_age > timedelta(days=2):
                security_alerts.append({
                    'level': 'warning',
                    'message': f'Latest backup is {backup_age.days} days old'
                })
        else:
            security_alerts.append({
                'level': 'danger',
                'message': 'No backups found'
            })
        
        conn.close()
        
        return render_template('admin/system_status.html',
                             system_info=system_info,
                             db_size=db_size,
                             security_alerts=security_alerts,
                             suspicious_ips=suspicious_ips)
                             
    except ImportError:
        flash('psutil package required for system monitoring', 'warning')
        return redirect(url_for('security.dashboard'))
    except Exception as e:
        flash(f'Error getting system status: {str(e)}', 'danger')
        return redirect(url_for('security.dashboard'))