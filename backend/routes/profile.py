"""
Profile Routes
===============
POST /api/profile/save        — save or update user profile + goals
GET  /api/profile/<user_id>   — get user profile and goals
"""

from flask import Blueprint, request, jsonify
from config.database import get_connection, get_cursor

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/save', methods=['POST'])
def save_profile():
    data    = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400

    goals = data.get('goals', [])

    # Collect only profile fields that were actually sent (not None)
    PROFILE_FIELDS = [
        'age', 'gender', 'caste', 'state', 'district',
        'occupation', 'annual_income', 'family_size',
        'land_owned_acres', 'has_bank_account', 'is_bpl', 'is_pwd', 'is_widow'
    ]
    profile_updates = {k: data[k] for k in PROFILE_FIELDS if k in data and data[k] is not None}

    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        # ── Save profile fields only if provided ──────────────
        if profile_updates:
            # Check if profile row exists
            cur.execute('SELECT profile_id FROM user_profiles WHERE user_id = %s', (user_id,))
            exists = cur.fetchone()

            if exists:
                # UPDATE only the fields that were sent
                set_clause = ', '.join([f"{k} = %({k})s" for k in profile_updates])
                set_clause += ', updated_at = NOW()'
                query = f"UPDATE user_profiles SET {set_clause} WHERE user_id = %(user_id)s"
                profile_updates['user_id'] = user_id
                cur.execute(query, profile_updates)
            else:
                # INSERT new row with provided fields
                cols = ', '.join(list(profile_updates.keys()) + ['user_id', 'updated_at'])
                vals = ', '.join([f"%({k})s" for k in profile_updates.keys()] + ['%(user_id)s', 'NOW()'])
                profile_updates['user_id'] = user_id
                cur.execute(f'INSERT INTO user_profiles ({cols}) VALUES ({vals})', profile_updates)

        # ── Save goals — replace all existing goals ───────────
        if goals:
            cur.execute('DELETE FROM user_goals WHERE user_id = %s', (user_id,))
            for goal in goals:
                cat  = goal.get('goal_category', '').strip()
                desc = goal.get('goal_description', '')
                if cat:
                    cur.execute('''
                        INSERT INTO user_goals (user_id, goal_category, goal_description)
                        VALUES (%s, %s, %s)
                    ''', (user_id, cat, desc))

        conn.commit()
        return jsonify({'success': True, 'message': 'Profile saved successfully'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()


@profile_bp.route('/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        cur.execute('SELECT * FROM user_profiles WHERE user_id = %s', (user_id,))
        profile = cur.fetchone()

        cur.execute('SELECT * FROM user_goals WHERE user_id = %s ORDER BY created_at', (user_id,))
        goals = cur.fetchall()

        if not profile:
            return jsonify({'success': False, 'message': 'Profile not found'}), 404

        return jsonify({
            'success': True,
            'profile': dict(profile),
            'goals'  : [dict(g) for g in goals]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()
