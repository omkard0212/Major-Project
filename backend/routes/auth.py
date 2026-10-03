"""
Auth Routes
============
POST /api/auth/register  — create new user account
POST /api/auth/login     — login and get session token
"""

import bcrypt
from flask import Blueprint, request, jsonify
from config.database import get_connection, get_cursor

auth_bp = Blueprint('auth', __name__)

# ── REGISTER ──────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Required fields
    name     = data.get('name', '').strip()
    phone    = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    language = data.get('preferred_language', 'hindi').strip()
    mode     = data.get('input_mode', 'text').strip()

    # Basic validation
    if not name or not phone or not password:
        return jsonify({'success': False, 'message': 'Name, phone and password are required'}), 400

    if len(phone) < 10:
        return jsonify({'success': False, 'message': 'Enter a valid phone number'}), 400

    if len(password) < 4:
        return jsonify({'success': False, 'message': 'Password must be at least 4 characters'}), 400

    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        # Check if phone already exists
        cur.execute('SELECT user_id FROM users WHERE phone = %s', (phone,))
        if cur.fetchone():
            return jsonify({'success': False, 'message': 'Phone number already registered'}), 409

        # Insert new user
        cur.execute('''
            INSERT INTO users (name, phone, password_hash, preferred_language, input_mode)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id, name, phone, preferred_language, input_mode, created_at
        ''', (name, phone, password_hash, language, mode))

        new_user = dict(cur.fetchone())
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'user'   : {
                'user_id'           : new_user['user_id'],
                'name'              : new_user['name'],
                'phone'             : new_user['phone'],
                'preferred_language': new_user['preferred_language'],
                'input_mode'        : new_user['input_mode'],
            }
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()


# ── LOGIN ─────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    phone    = data.get('phone', '').strip()
    password = data.get('password', '').strip()

    if not phone or not password:
        return jsonify({'success': False, 'message': 'Phone and password are required'}), 400

    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        # Find user by phone
        cur.execute('''
            SELECT user_id, name, phone, password_hash,
                   preferred_language, input_mode
            FROM users WHERE phone = %s
        ''', (phone,))

        user = cur.fetchone()

        if not user:
            return jsonify({'success': False, 'message': 'Phone number not registered'}), 404

        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'success': False, 'message': 'Incorrect password'}), 401

        # Update last login time
        cur.execute('UPDATE users SET last_login = NOW() WHERE user_id = %s', (user['user_id'],))
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user'   : {
                'user_id'           : user['user_id'],
                'name'              : user['name'],
                'phone'             : user['phone'],
                'preferred_language': user['preferred_language'],
                'input_mode'        : user['input_mode'],
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()
