import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from security_config import configure_security, UPLOAD_FOLDERS
from datetime import timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure security
csrf, limiter = configure_security(app)

# Configure upload folders
for folder_type, folder_path in UPLOAD_FOLDERS.items():
    os.makedirs(folder_path, exist_ok=True)

# Legacy upload folder support
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

@app.before_request
def load_global_context():
    if session.get('user_id'):
        # Load current logo for all authenticated pages
        conn = database.get_db_connection()
        try:
            logo_setting = conn.execute("SELECT setting_value FROM settings WHERE setting_name = 'system_logo'").fetchone()
            g.current_logo = logo_setting['setting_value'] if logo_setting else None
        except:
            g.current_logo = None
        finally:
            conn.close()
    else:
        g.current_logo = None

@app.context_processor
def inject_global_context():
    return dict(current_logo=g.current_logo)

# Import and register blueprints
from routes.admin import admin_bp
from routes.hr import hr_bp
from routes.employee import employee_bp
from routes.kiosk import kiosk_bp
from routes.settings import settings_bp
from routes.exports import exports_bp
from routes.applications import applications_bp
from routes.chat import chat_bp
from routes.security import security_bp
from auth import auth_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(hr_bp, url_prefix='/hr')
app.register_blueprint(employee_bp, url_prefix='/employee')
app.register_blueprint(kiosk_bp, url_prefix='/kiosk')
app.register_blueprint(settings_bp)
app.register_blueprint(exports_bp)
app.register_blueprint(applications_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(security_bp)

from auth import login_required
from flask import render_template, redirect, url_for, session, g
import database

@app.route('/')
def index():
    # Show public homepage for non-authenticated users
    if 'user_id' not in session:
        return render_template('homepage.html')
    
    # Redirect authenticated users to their dashboards
    role = session.get('role')
    if role == 'Admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'HR':
        return redirect(url_for('hr.dashboard'))
    elif role == 'Employee':
        return redirect(url_for('employee.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@app.route('/kiosk')
def kiosk_redirect():
    return redirect(url_for('kiosk.punch'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
