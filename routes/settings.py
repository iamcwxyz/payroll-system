from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth import login_required, role_required
import database
from datetime import datetime
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
@role_required(['Admin', 'HR'])
def settings():
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM settings ORDER BY setting_name")
    settings_list = c.fetchall()
    
    # Get current logo
    logo_setting = c.execute("SELECT setting_value FROM settings WHERE setting_name = 'system_logo'").fetchone()
    current_logo = logo_setting['setting_value'] if logo_setting else None
    
    conn.close()
    return render_template('settings/settings.html', settings=settings_list, current_logo=current_logo)

@settings_bp.route('/settings/update', methods=['POST'])
@login_required
@role_required(['Admin', 'HR'])
def update_settings():
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Handle logo upload
    if 'system_logo' in request.files:
        file = request.files['system_logo']
        if file and file.filename:
            from werkzeug.utils import secure_filename
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
            if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = f"logo_{timestamp}_{filename}"
                file_path = os.path.join('static/images', filename)
                file.save(file_path)
                
                # Update or insert logo setting
                existing = c.execute("SELECT 1 FROM settings WHERE setting_name = 'system_logo'").fetchone()
                if existing:
                    c.execute("UPDATE settings SET setting_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE setting_name = 'system_logo'", 
                             (filename, session['user_id']))
                else:
                    c.execute("INSERT INTO settings (setting_name, setting_value, description, updated_by, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                             ('system_logo', filename, 'System logo image file', session['user_id']))
    
    for key, value in request.form.items():
        if key.startswith('setting_'):
            setting_name = key.replace('setting_', '')
            c.execute("UPDATE settings SET setting_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE setting_name = ?", 
                     (value, session['user_id'], setting_name))
    
    conn.commit()
    conn.close()
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('settings.settings'))