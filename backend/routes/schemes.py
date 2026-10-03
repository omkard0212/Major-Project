"""
Schemes Routes
===============
POST /api/schemes/recommend         — get scheme recommendations for a user
POST /api/schemes/interaction       — log a user interaction (view/select/apply)
GET  /api/schemes/history/<user_id> — get past recommendations for a user
"""

from flask import Blueprint, request, jsonify
from config.database import get_connection, get_cursor
from recommender import recommend, record_interaction

schemes_bp = Blueprint('schemes', __name__)

# ── Goal category → occupation + scheme category mapping ─────
# Maps user goals to the fields the ML model understands
GOAL_TO_PROFILE = {
    'education'        : {'occupation_hint': 'student',      'category_hint': 'Education & Learning'},
    'farming'          : {'occupation_hint': 'farmer',       'category_hint': 'Agriculture,Rural & Environment'},
    'business'         : {'occupation_hint': 'entrepreneur', 'category_hint': 'Business & Entrepreneurship'},
    'health'           : {'occupation_hint': None,           'category_hint': 'Health & Wellness'},
    'housing'          : {'occupation_hint': None,           'category_hint': 'Social welfare & Empowerment'},
    'insurance'        : {'occupation_hint': None,           'category_hint': 'Banking,Financial Services and Insurance'},
    'employment'       : {'occupation_hint': None,           'category_hint': 'Skills & Employment'},
    'women_empowerment': {'occupation_hint': None,           'category_hint': 'Women and Child'},
    'social_welfare'   : {'occupation_hint': None,           'category_hint': 'Social welfare & Empowerment'},
    'other'            : {'occupation_hint': None,           'category_hint': None},
}

# ── RECOMMEND ─────────────────────────────────────────────────
@schemes_bp.route('/recommend', methods=['POST'])
def get_recommendations():
    data    = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400

    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        # Fetch user profile from database
        cur.execute('SELECT * FROM user_profiles WHERE user_id = %s', (user_id,))
        profile = cur.fetchone()

        if not profile:
            return jsonify({'success': False, 'message': 'Profile not found. Please complete your profile first.'}), 404

        # Fetch user goals
        cur.execute('SELECT goal_category, goal_description FROM user_goals WHERE user_id = %s', (user_id,))
        goals = cur.fetchall()

        # Fetch user name
        cur.execute('SELECT name FROM users WHERE user_id = %s', (user_id,))
        user_row = cur.fetchone()
        user_name = user_row['name'] if user_row else ''

        # Build ML model user profile — sanitize None values to empty string
        user_profile = {
            'name'          : user_name or '',
            'age'           : profile['age'],
            'annual_income' : profile['annual_income'],
            'gender'        : profile['gender']     or 'any',
            'caste'         : profile['caste']      or '',
            'state'         : profile['state']      or '',
            'occupation'    : profile['occupation'] or 'any',
        }

        # Add BPL / widow / PWD flags to occupation if applicable
        extra_occs = []
        if profile['is_bpl']:
            extra_occs.append('bpl')
        if profile['is_pwd']:
            extra_occs.append('pwd')
        if profile['is_widow']:
            extra_occs.append('widow')

        if extra_occs and user_profile.get('occupation'):
            user_profile['occupation'] = user_profile['occupation'] + ',' + ','.join(extra_occs)
        elif extra_occs:
            user_profile['occupation'] = ','.join(extra_occs)

        # Run the ML recommender
        result = recommend(user_profile, top_n=5)

        if result['eligible_count'] == 0:
            return jsonify({
                'success'        : True,
                'eligible_count' : 0,
                'recommendations': [],
                'message'        : 'No schemes found matching your profile. Try updating your details.'
            }), 200

        # Save recommendations to database
        for rec in result['recommendations']:
            cur.execute('''
                INSERT INTO scheme_recommendations
                    (user_id, scheme_slug, scheme_name, score, rank)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, rec['slug'], rec['scheme_name'], rec['score'], rec['rank']))

        conn.commit()

        return jsonify({
            'success'        : True,
            'eligible_count' : result['eligible_count'],
            'recommendations': result['recommendations']
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()


# ── LOG INTERACTION ───────────────────────────────────────────
@schemes_bp.route('/interaction', methods=['POST'])
def log_interaction():
    data = request.get_json()

    user_id     = data.get('user_id')
    scheme_slug = data.get('scheme_slug')
    scheme_name = data.get('scheme_name')
    action      = data.get('action')
    score       = data.get('score', 0.0)

    if not all([user_id, scheme_slug, scheme_name, action]):
        return jsonify({'success': False, 'message': 'user_id, scheme_slug, scheme_name and action are required'}), 400

    if action not in ('view', 'select', 'apply'):
        return jsonify({'success': False, 'message': 'action must be view, select or apply'}), 400

    ACTION_WEIGHTS = {'view': 1, 'select': 3, 'apply': 5}

    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        # Fetch user profile for ML logger
        cur.execute('SELECT * FROM user_profiles WHERE user_id = %s', (user_id,))
        profile = cur.fetchone()

        # Save to PostgreSQL
        cur.execute('''
            INSERT INTO user_interactions
                (user_id, scheme_slug, scheme_name, action, action_weight, score_given)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_id, scheme_slug, scheme_name, action, ACTION_WEIGHTS[action], score))

        conn.commit()

        # Also log to ML model's JSON file for learning layer
        if profile:
            user_profile = {
                'age'           : profile['age'],
                'annual_income' : profile['annual_income'],
                'gender'        : profile['gender'],
                'caste'         : profile['caste'],
                'state'         : profile['state'],
                'occupation'    : profile['occupation'],
            }
            record_interaction(user_profile, scheme_slug, scheme_name, action, score)

        return jsonify({'success': True, 'message': 'Interaction logged'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()


# ── GET HISTORY ───────────────────────────────────────────────
@schemes_bp.route('/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    conn = None
    try:
        conn = get_connection()
        cur  = get_cursor(conn)

        cur.execute('''
            SELECT scheme_slug, scheme_name, score, rank, recommended_at
            FROM scheme_recommendations
            WHERE user_id = %s
            ORDER BY recommended_at DESC
            LIMIT 20
        ''', (user_id,))

        history = [dict(row) for row in cur.fetchall()]

        return jsonify({'success': True, 'history': history}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

    finally:
        if conn:
            conn.close()
