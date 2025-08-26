from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from auth import login_required, role_required
import database
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
@login_required
def chat_dashboard():
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Get user's chat rooms with unread message count and participant details for direct chats
    c.execute("""
        SELECT cr.*, COUNT(DISTINCT rm.member_id) as member_count,
               COUNT(CASE WHEN cm.sent_at > user_rm.last_read_at AND cm.sender_id != ? THEN 1 END) as unread_count,
               CASE 
                   WHEN cr.room_type = 'direct' THEN 
                       (SELECT e.name FROM employees e 
                        JOIN room_memberships rm_other ON e.id = rm_other.member_id 
                        WHERE rm_other.room_id = cr.id AND rm_other.member_id != ? AND rm_other.member_type = 'employee')
                   ELSE cr.room_name 
               END as display_name,
               CASE 
                   WHEN cr.room_type = 'direct' THEN 
                       (SELECT e.profile_picture FROM employees e 
                        JOIN room_memberships rm_other ON e.id = rm_other.member_id 
                        WHERE rm_other.room_id = cr.id AND rm_other.member_id != ? AND rm_other.member_type = 'employee')
                   ELSE NULL 
               END as participant_picture
        FROM chat_rooms cr
        LEFT JOIN room_memberships rm ON cr.id = rm.room_id
        JOIN room_memberships user_rm ON cr.id = user_rm.room_id
        LEFT JOIN chat_messages cm ON cr.id = cm.room_id
        WHERE user_rm.member_id = ? AND user_rm.member_type = 'employee'
        GROUP BY cr.id, user_rm.last_read_at
        ORDER BY cr.created_at DESC
    """, (session['user_id'], session['user_id'], session['user_id'], session['user_id']))
    user_rooms = c.fetchall()
    
    # Get public rooms (general chat)
    c.execute("""
        SELECT cr.*, COUNT(rm.member_id) as member_count
        FROM chat_rooms cr
        LEFT JOIN room_memberships rm ON cr.id = rm.room_id
        WHERE cr.room_type = 'general'
        GROUP BY cr.id
    """)
    public_rooms = c.fetchall()
    
    # Get all employees for direct messaging
    c.execute("""
        SELECT id, employee_id, name, department, role, profile_picture
        FROM employees 
        WHERE status = 'Active' AND id != ?
        ORDER BY name
    """, (session['user_id'],))
    all_employees = c.fetchall()
    
    conn.close()
    return render_template('chat/dashboard.html', user_rooms=user_rooms, public_rooms=public_rooms, all_employees=all_employees)

@chat_bp.route('/chat/create', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        room_name = request.form['room_name']
        room_type = request.form.get('room_type', 'group')
        join_code = database.generate_join_code()
        
        conn = database.get_db_connection()
        c = conn.cursor()
        
        # Create room
        c.execute("""INSERT INTO chat_rooms (room_name, room_type, join_code, created_by) 
                     VALUES (?, ?, ?, ?)""", (room_name, room_type, join_code, session['user_id']))
        room_id = c.lastrowid
        
        # Add creator to room
        c.execute("""INSERT INTO room_memberships (room_id, member_id, member_type) 
                     VALUES (?, ?, 'employee')""", (room_id, session['user_id']))
        
        conn.commit()
        conn.close()
        
        flash(f'Chat room created! Join code: {join_code}', 'success')
        return redirect(url_for('chat.room', room_id=room_id))
    
    return render_template('chat/create_room.html')

@chat_bp.route('/chat/join', methods=['GET', 'POST'])
@login_required
def join_room():
    if request.method == 'POST':
        join_code = request.form['join_code'].upper()
        
        conn = database.get_db_connection()
        c = conn.cursor()
        
        # Find room by join code
        c.execute("SELECT * FROM chat_rooms WHERE join_code = ? AND is_active = 1", (join_code,))
        room = c.fetchone()
        
        if not room:
            flash('Invalid join code. Please check and try again.', 'error')
            return redirect(url_for('chat.join_room'))
        
        # Check if already a member
        c.execute("SELECT 1 FROM room_memberships WHERE room_id = ? AND member_id = ? AND member_type = 'employee'", 
                 (room['id'], session['user_id']))
        if c.fetchone():
            flash('You are already a member of this chat room.', 'info')
            return redirect(url_for('chat.room', room_id=room['id']))
        
        # Add user to room
        c.execute("INSERT INTO room_memberships (room_id, member_id, member_type) VALUES (?, ?, 'employee')", 
                 (room['id'], session['user_id']))
        conn.commit()
        conn.close()
        
        flash(f'Successfully joined "{room["room_name"]}"!', 'success')
        return redirect(url_for('chat.room', room_id=room['id']))
    
    return render_template('chat/join_room.html')

@chat_bp.route('/chat/direct/<int:employee_id>')
@login_required
def start_direct_chat(employee_id):
    if employee_id == session['user_id']:
        flash('Cannot chat with yourself.', 'error')
        return redirect(url_for('chat.chat_dashboard'))
    
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Check if direct chat already exists between these users
    c.execute("""
        SELECT cr.id FROM chat_rooms cr
        JOIN room_memberships rm1 ON cr.id = rm1.room_id
        JOIN room_memberships rm2 ON cr.id = rm2.room_id
        WHERE cr.room_type = 'direct' 
        AND rm1.member_id = ? AND rm1.member_type = 'employee'
        AND rm2.member_id = ? AND rm2.member_type = 'employee'
        AND (SELECT COUNT(*) FROM room_memberships WHERE room_id = cr.id) = 2
    """, (session['user_id'], employee_id))
    existing_room = c.fetchone()
    
    if existing_room:
        conn.close()
        return redirect(url_for('chat.room', room_id=existing_room['id']))
    
    # Get other employee's name
    c.execute("SELECT name FROM employees WHERE id = ?", (employee_id,))
    other_employee = c.fetchone()
    if not other_employee:
        flash('Employee not found.', 'error')
        conn.close()
        return redirect(url_for('chat.chat_dashboard'))
    
    # Create new direct chat room with employee name
    room_name = f"{other_employee['name']}"
    c.execute("""INSERT INTO chat_rooms (room_name, room_type, created_by) 
                 VALUES (?, 'direct', ?)""", (room_name, session['user_id']))
    room_id = c.lastrowid
    
    # Add both users to the room
    c.execute("""INSERT INTO room_memberships (room_id, member_id, member_type) 
                 VALUES (?, ?, 'employee')""", (room_id, session['user_id']))
    c.execute("""INSERT INTO room_memberships (room_id, member_id, member_type) 
                 VALUES (?, ?, 'employee')""", (room_id, employee_id))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('chat.room', room_id=room_id))

@chat_bp.route('/chat/room/<int:room_id>')
@login_required
def room(room_id):
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Verify user is member of this room
    c.execute("""SELECT 1 FROM room_memberships 
                 WHERE room_id = ? AND member_id = ? AND member_type = 'employee'""", 
             (room_id, session['user_id']))
    if not c.fetchone():
        flash('You are not a member of this chat room.', 'error')
        return redirect(url_for('chat.chat_dashboard'))
    
    # Get room info
    c.execute("SELECT * FROM chat_rooms WHERE id = ?", (room_id,))
    room_info = c.fetchone()
    
    # Get messages with profile pictures
    c.execute("""
        SELECT cm.*, e.name as sender_name, e.employee_id, e.profile_picture
        FROM chat_messages cm
        LEFT JOIN employees e ON cm.sender_id = e.id
        WHERE cm.room_id = ?
        ORDER BY cm.sent_at ASC
    """, (room_id,))
    messages = c.fetchall()
    
    # Get room members with profile pictures
    c.execute("""
        SELECT e.name, e.employee_id, e.role, e.profile_picture
        FROM room_memberships rm
        JOIN employees e ON rm.member_id = e.id
        WHERE rm.room_id = ? AND rm.member_type = 'employee'
        ORDER BY e.name
    """, (room_id,))
    members = c.fetchall()
    
    # Mark room as read for current user
    c.execute("""UPDATE room_memberships 
                 SET last_read_at = CURRENT_TIMESTAMP 
                 WHERE room_id = ? AND member_id = ? AND member_type = 'employee'""", 
             (room_id, session['user_id']))
    conn.commit()
    
    conn.close()
    return render_template('chat/room.html', room=room_info, messages=messages, members=members)

@chat_bp.route('/chat/room/<int:room_id>/send', methods=['POST'])
@login_required
def send_message(room_id):
    message = request.form['message'].strip()
    if not message:
        return redirect(url_for('chat.room', room_id=room_id))
    
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Verify user is member
    c.execute("SELECT 1 FROM room_memberships WHERE room_id = ? AND member_id = ? AND member_type = 'employee'", 
             (room_id, session['user_id']))
    if not c.fetchone():
        flash('Access denied.', 'error')
        return redirect(url_for('chat.chat_dashboard'))
    
    # Send message
    c.execute("""INSERT INTO chat_messages (room_id, sender_id, sender_type, message) 
                 VALUES (?, ?, 'employee', ?)""", (room_id, session['user_id'], message))
    conn.commit()
    conn.close()
    
    return redirect(url_for('chat.room', room_id=room_id))

@chat_bp.route('/chat/room/<int:room_id>/messages')
@login_required
def get_messages(room_id):
    """API endpoint for real-time message loading"""
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Verify access
    c.execute("SELECT 1 FROM room_memberships WHERE room_id = ? AND member_id = ? AND member_type = 'employee'", 
             (room_id, session['user_id']))
    if not c.fetchone():
        return jsonify({'error': 'Access denied'}), 403
    
    # Get recent messages
    since = request.args.get('since', '1970-01-01 00:00:00')
    c.execute("""
        SELECT cm.*, e.name as sender_name, e.employee_id
        FROM chat_messages cm
        LEFT JOIN employees e ON cm.sender_id = e.id
        WHERE cm.room_id = ? AND cm.sent_at > ?
        ORDER BY cm.sent_at ASC
    """, (room_id, since))
    messages = c.fetchall()
    
    conn.close()
    
    return jsonify([{
        'id': msg['id'],
        'sender_name': msg['sender_name'],
        'employee_id': msg['employee_id'],
        'message': msg['message'],
        'sent_at': msg['sent_at'],
        'is_own': msg['sender_id'] == session['user_id']
    } for msg in messages])