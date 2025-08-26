# Payroll & Attendance System

## Overview

This is a comprehensive web-based payroll and attendance management system built with Flask. The system provides role-based access control for Admins, HR personnel, and Employees, along with a kiosk mode for time tracking. It manages employee records, attendance tracking, leave requests, and payroll generation with an intuitive web interface.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask**: Python web framework chosen for its simplicity and flexibility
- **Blueprint Architecture**: Modular route organization separating concerns by user role (admin, hr, employee, kiosk, auth)
- **Session-based Authentication**: Simple session management for user authentication and role-based access control

### Database Layer
- **SQLite**: Lightweight file-based database for development and deployment simplicity
- **Raw SQL**: Direct SQL queries using sqlite3 for database operations
- **Schema Design**: Three core tables (employees, attendance, leaves) with foreign key relationships

### Frontend Architecture
- **Jinja2 Templates**: Server-side rendering with template inheritance using a base layout
- **Bootstrap 5**: CSS framework with dark theme for responsive, modern UI
- **Font Awesome**: Icon library for visual enhancement
- **Role-based UI**: Different dashboards and navigation based on user roles

### Authentication & Authorization
- **Simple Password Authentication**: Basic username/password login (no hashing implemented)
- **Session Management**: Flask sessions for maintaining user state
- **Role-based Access Control**: Decorators (`@login_required`, `@role_required`) for protecting routes
- **Three User Roles**: Admin (full access), HR (leave/attendance management), Employee (self-service)

### File Upload System
- **Profile Pictures**: Secure file upload with extension validation
- **Static File Serving**: Files stored in `static/uploads/` directory
- **File Size Limits**: 16MB maximum upload size configured

### Application Structure
- **Modular Design**: Separate route files for each user role
- **Centralized Database**: Single database module for connection management
- **Static Assets**: CSS, JS, and uploaded files served from static directory
- **Template Hierarchy**: Base template with role-specific extensions

### Key Features
- **Attendance Tracking**: Time-in/time-out with kiosk mode interface
- **Leave Management**: Employee requests with HR approval workflow
- **Payroll System**: Automated payroll calculation based on attendance
- **Employee Management**: Admin capabilities for adding/managing employees
- **Dashboard Analytics**: Role-specific dashboards with key metrics

## External Dependencies

### Python Packages
- **Flask**: Web framework for application routing and request handling
- **Werkzeug**: WSGI utilities including ProxyFix for deployment and secure filename handling

### Frontend Libraries (CDN)
- **Bootstrap 5**: CSS framework with dark theme variant from Replit CDN
- **Font Awesome 6**: Icon library from CloudFlare CDN

### Database
- **SQLite**: Built-in Python database, no external database server required
- **File Storage**: Database stored as local file (`payroll_system.db`)

### Development Tools
- **Python Standard Library**: sqlite3, datetime, os, logging modules
- **No External APIs**: Self-contained system with no third-party service integrations