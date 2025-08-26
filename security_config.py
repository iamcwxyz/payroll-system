"""
Security configuration module for the payroll system
Implements enterprise-grade security features
"""

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from datetime import timedelta

def configure_security(app: Flask):
    """Configure comprehensive security settings for the Flask app"""
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri="memory://"
    )
    
    # Specific rate limits for sensitive endpoints
    @limiter.limit("5 per minute")
    def login_limiter():
        pass
    
    # Security Headers
    @app.after_request
    def set_security_headers(response):
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Strict Transport Security (HTTPS only)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net cdn.replit.com; "
            "style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com cdn.jsdelivr.net cdn.replit.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' cdnjs.cloudflare.com; "
            "connect-src 'self';"
        )
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Feature Policy / Permissions Policy
        response.headers['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "fullscreen=(self)"
        )
        
        return response
    
    # Session Configuration
    app.config.update(
        # Session security
        SESSION_COOKIE_SECURE=True,  # HTTPS only
        SESSION_COOKIE_HTTPONLY=True,  # No JavaScript access
        SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),  # 8 hour timeout
        
        # File Upload Security
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        
        # CSRF Configuration
        WTF_CSRF_TIME_LIMIT=None,  # No time limit for CSRF tokens
        WTF_CSRF_SSL_STRICT=False,  # Allow for development without HTTPS
        WTF_CSRF_ENABLED=True,  # Enable CSRF protection
        
        # Security Keys
        SECRET_KEY=os.environ.get('SESSION_SECRET', 'dev-key-change-in-production'),
        WTF_CSRF_SECRET_KEY=os.environ.get('CSRF_SECRET', 'csrf-key-change-in-production'),
    )
    
    return csrf, limiter

# Password Policy Configuration
PASSWORD_REQUIREMENTS = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_numbers': True,
    'require_special_chars': True,
    'forbidden_patterns': [
        'password', '123456', 'admin', 'user', 'login',
        'qwerty', 'abc123', 'password123'
    ]
}

# File Upload Security Configuration
ALLOWED_EXTENSIONS = {
    'images': {'png', 'jpg', 'jpeg', 'gif', 'svg'},
    'documents': {'pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls'},
    'resumes': {'pdf', 'doc', 'docx', 'txt'}
}

UPLOAD_FOLDERS = {
    'profiles': 'static/uploads/profiles',
    'resumes': 'static/uploads/resumes',
    'documents': 'static/uploads/documents',
    'logo': 'static/images'
}

# Network Security Configuration
TRUSTED_PROXIES = ['127.0.0.1', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']

# Logging Configuration for Security Events
SECURITY_LOG_CONFIG = {
    'log_level': 'INFO',
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': 'logs/security.log',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# API Security Configuration
API_RATE_LIMITS = {
    'default': '100 per hour',
    'auth': '5 per minute',
    'file_upload': '10 per hour',
    'payroll': '20 per hour',
    'chat': '1000 per hour'
}