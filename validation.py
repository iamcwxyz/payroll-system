"""
Input validation and security module
Provides comprehensive validation for all user inputs
"""

import re
from flask import flash
from database import sanitize_input
from security_config import PASSWORD_REQUIREMENTS
import bleach

class InputValidator:
    """Comprehensive input validation class"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email:
            return False, "Email is required"
        
        email = sanitize_input(email)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False, "Invalid email format"
        
        if len(email) > 254:
            return False, "Email too long"
            
        return True, email
    
    @staticmethod
    def validate_password(password, confirm_password=None):
        """Validate password according to security requirements"""
        if not password:
            return False, "Password is required"
        
        requirements = PASSWORD_REQUIREMENTS
        errors = []
        
        if len(password) < requirements['min_length']:
            errors.append(f"Password must be at least {requirements['min_length']} characters long")
        
        if requirements['require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if requirements['require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if requirements['require_numbers'] and not re.search(r'[0-9]', password):
            errors.append("Password must contain at least one number")
        
        if requirements['require_special_chars'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for forbidden patterns
        password_lower = password.lower()
        for pattern in requirements['forbidden_patterns']:
            if pattern.lower() in password_lower:
                errors.append(f"Password cannot contain '{pattern}'")
                break
        
        if confirm_password is not None and password != confirm_password:
            errors.append("Passwords do not match")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, password
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username:
            return False, "Username is required"
        
        username = sanitize_input(username)
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username too long (maximum 50 characters)"
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, dots, and hyphens"
        
        return True, username
    
    @staticmethod
    def validate_name(name, field_name="Name"):
        """Validate person name"""
        if not name:
            return False, f"{field_name} is required"
        
        name = sanitize_input(name)
        
        if len(name) < 2:
            return False, f"{field_name} must be at least 2 characters long"
        
        if len(name) > 100:
            return False, f"{field_name} too long (maximum 100 characters)"
        
        # Allow letters, spaces, apostrophes, and hyphens
        if not re.match(r"^[a-zA-Z\s'-]+$", name):
            return False, f"{field_name} can only contain letters, spaces, apostrophes, and hyphens"
        
        return True, name
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number"""
        if not phone:
            return False, "Phone number is required"
        
        phone = sanitize_input(phone)
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) < 10:
            return False, "Phone number must have at least 10 digits"
        
        if len(digits_only) > 15:
            return False, "Phone number too long"
        
        return True, phone
    
    @staticmethod
    def validate_employee_id(employee_id):
        """Validate employee ID format"""
        if not employee_id:
            return False, "Employee ID is required"
        
        employee_id = sanitize_input(employee_id)
        
        if not re.match(r'^EMP\d{3,}$', employee_id):
            return False, "Employee ID must follow format: EMP001, EMP002, etc."
        
        return True, employee_id
    
    @staticmethod
    def validate_salary(salary):
        """Validate salary amount"""
        if not salary:
            return False, "Salary is required"
        
        try:
            salary_float = float(salary)
            if salary_float < 0:
                return False, "Salary cannot be negative"
            if salary_float > 1000000:
                return False, "Salary amount too high"
            return True, salary_float
        except ValueError:
            return False, "Invalid salary format"
    
    @staticmethod
    def validate_text_input(text, field_name, min_length=0, max_length=500, required=True):
        """Generic text input validation"""
        if not text and required:
            return False, f"{field_name} is required"
        
        if not text:
            return True, ""
        
        text = sanitize_input(text)
        
        if len(text) < min_length:
            return False, f"{field_name} must be at least {min_length} characters long"
        
        if len(text) > max_length:
            return False, f"{field_name} too long (maximum {max_length} characters)"
        
        return True, text
    
    @staticmethod
    def validate_date_range(start_date, end_date):
        """Validate date range"""
        from datetime import datetime
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start > end:
                return False, "Start date cannot be after end date"
            
            # Check if dates are not too far in the future (1 year)
            now = datetime.now()
            if start.year - now.year > 1:
                return False, "Start date cannot be more than 1 year in the future"
            
            return True, (start_date, end_date)
        except ValueError:
            return False, "Invalid date format"
    
    @staticmethod
    def validate_role(role):
        """Validate user role"""
        valid_roles = ['Admin', 'HR', 'Employee']
        
        if role not in valid_roles:
            return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        
        return True, role
    
    @staticmethod
    def validate_department(department):
        """Validate department name"""
        if not department:
            return False, "Department is required"
        
        department = sanitize_input(department)
        
        if len(department) < 2:
            return False, "Department name must be at least 2 characters long"
        
        if len(department) > 50:
            return False, "Department name too long"
        
        return True, department

def secure_form_data(form_data):
    """Sanitize all form data to prevent XSS attacks"""
    sanitized_data = {}
    
    for key, value in form_data.items():
        if isinstance(value, str):
            sanitized_data[key] = sanitize_input(value)
        else:
            sanitized_data[key] = value
    
    return sanitized_data

def validate_csrf_token():
    """Additional CSRF validation for critical operations"""
    from flask import session, request
    
    # This will be handled by Flask-WTF automatically
    # This function is for additional custom validation if needed
    return True