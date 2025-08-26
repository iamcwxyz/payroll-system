from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import get_db_connection, log_security_event
import bcrypt
from datetime import datetime, timedelta
import secrets
import bleach

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        
        # Check session timeout (8 hours)
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > timedelta(hours=8):
                log_security_event('SESSION_TIMEOUT', session['user_id'], request.remote_addr, "Session timed out")
                session.clear()
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            user_role = session.get('role')
            
            # Admin and HR have full access to everything
            if user_role in ['Admin', 'HR']:
                return f(*args, **kwargs)
            
            # Handle role parameter as list or string
            if isinstance(role, list):
                allowed_roles = role
            else:
                allowed_roles = [role]
            
            # Check if user role matches any allowed role
            if user_role in allowed_roles:
                return f(*args, **kwargs)
            else:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('index'))
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM employees WHERE username = ? AND status = "Active"', 
                           (username,)).fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            # Generate secure session token
            session_token = secrets.token_urlsafe(32)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            session['employee_id'] = user['employee_id']
            session['session_token'] = session_token
            session['login_time'] = datetime.now().isoformat()
            session.permanent = True
            current_app.permanent_session_lifetime = timedelta(hours=8)
            
            # Log successful login
            log_security_event('LOGIN_SUCCESS', user['id'], request.remote_addr, f"User {user['username']} logged in successfully")
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            
            # Redirect based on role
            if user['role'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'HR':
                return redirect(url_for('hr.dashboard'))
            elif user['role'] == 'Employee':
                return redirect(url_for('employee.dashboard'))
        else:
            # Log failed login attempt
            log_security_event('LOGIN_FAILED', None, request.remote_addr, f"Failed login attempt for username: {username}")
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        log_security_event('LOGOUT', session['user_id'], request.remote_addr, f"User {session.get('username')} logged out")
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
