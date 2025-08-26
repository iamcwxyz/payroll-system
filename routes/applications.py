from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth import login_required, role_required
import database
import os
from werkzeug.utils import secure_filename
from datetime import datetime

applications_bp = Blueprint('applications', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@applications_bp.route('/apply')
def apply_form():
    return render_template('public/apply.html')

@applications_bp.route('/apply/submit', methods=['POST'])
def submit_application():
    try:
        # Generate application ID
        app_id = database.generate_application_id()
        
        # Handle file upload
        resume_file = None
        if 'resume' in request.files:
            file = request.files['resume']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{app_id}_{file.filename}")
                file_path = os.path.join('static/uploads/resumes', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                resume_file = filename
        
        # Insert application
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO applications 
                     (application_id, full_name, email, phone, address, position_applied, 
                      resume_file, work_experience, education, skills, status, applied_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', CURRENT_TIMESTAMP)''',
                  (app_id, request.form['full_name'], request.form['email'], 
                   request.form['phone'], request.form['address'], request.form['position'],
                   resume_file, request.form['work_experience'], request.form['education'],
                   request.form['skills']))
        conn.commit()
        conn.close()
        
        return render_template('public/application_success.html', application_id=app_id)
        
    except Exception as e:
        flash(f'Error submitting application: {str(e)}', 'error')
        return redirect(url_for('applications.apply_form'))

@applications_bp.route('/apply/status')
def check_status():
    return render_template('public/check_status.html')

@applications_bp.route('/apply/status/check', methods=['POST'])
def status_lookup():
    app_id = request.form['application_id']
    
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM applications WHERE application_id = ?", (app_id,))
    application = c.fetchone()
    conn.close()
    
    if application:
        return render_template('public/status_result.html', application=application)
    else:
        flash('Application ID not found. Please check your ID and try again.', 'error')
        return redirect(url_for('applications.check_status'))

@applications_bp.route('/hr/applications')
@login_required
@role_required(['Admin', 'HR'])
def manage_applications():
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT * FROM applications ORDER BY 
                 CASE status 
                     WHEN 'Pending' THEN 1 
                     WHEN 'In Review' THEN 2 
                     ELSE 3 
                 END, applied_date DESC""")
    applications = c.fetchall()
    conn.close()
    return render_template('hr/applications.html', applications=applications)

@applications_bp.route('/hr/applications/<int:app_id>')
@login_required
@role_required(['Admin', 'HR'])
def view_application(app_id):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    application = c.fetchone()
    conn.close()
    
    if not application:
        flash('Application not found.', 'error')
        return redirect(url_for('applications.manage_applications'))
    
    return render_template('hr/view_application.html', application=application)

@applications_bp.route('/hr/applications/<int:app_id>/update', methods=['POST'])
@login_required
@role_required(['Admin', 'HR'])
def update_application_status(app_id):
    status = request.form['status']
    notes = request.form.get('notes', '')
    
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("""UPDATE applications 
                 SET status = ?, notes = ?, processed_by = ?, processed_date = CURRENT_TIMESTAMP 
                 WHERE id = ?""", (status, notes, session['user_id'], app_id))
    conn.commit()
    conn.close()
    
    flash('Application status updated successfully!', 'success')
    return redirect(url_for('applications.view_application', app_id=app_id))