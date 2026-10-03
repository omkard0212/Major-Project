"""
Step 4 — User Interaction Logger
===================================
Records every time a user interacts with a scheme.
Stored in a local JSON file: user_interactions.json

Each log entry captures:
  - timestamp
  - user profile (age, income, gender, caste, state, occupation)
  - scheme slug (unique ID of the scheme)
  - scheme name
  - action type: 'view' / 'select' / 'apply'
  - score the scheme received when it was shown

Action weights (used by learning layer in Step 5):
  - 'view'   : user clicked to read more          → weight 1
  - 'select' : user bookmarked / saved the scheme → weight 3
  - 'apply'  : user clicked to apply              → weight 5

The learning layer aggregates these to compute popularity boost per scheme.
"""

import os
import json
from datetime import datetime

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
INTERACTIONS_FILE = os.path.join(BASE_DIR, 'user_interactions.json')

# How much each action type counts
ACTION_WEIGHTS = {
    'view'  : 1,
    'select': 3,
    'apply' : 5,
}

# ── Load all interactions ──────────────────────────────────────
def load_interactions():
    if not os.path.exists(INTERACTIONS_FILE):
        return []
    with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# ── Save all interactions ──────────────────────────────────────
def save_interactions(interactions):
    with open(INTERACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(interactions, f, indent=2, ensure_ascii=False)

# ── Log a single interaction ───────────────────────────────────
def log_interaction(user_profile, scheme_slug, scheme_name, action, score_given=0.0):
    """
    Record one user-scheme interaction.

    Args:
        user_profile  : dict with user's age, caste, state, occupation etc.
        scheme_slug   : unique string ID of the scheme (from CSV)
        scheme_name   : human readable name
        action        : 'view' / 'select' / 'apply'
        score_given   : the score the scheme received when shown to this user
    """
    if action not in ACTION_WEIGHTS:
        raise ValueError(f"Invalid action '{action}'. Must be: view, select, apply")

    entry = {
        'timestamp'  : datetime.now().isoformat(),
        'action'     : action,
        'action_weight': ACTION_WEIGHTS[action],
        'scheme_slug': scheme_slug,
        'scheme_name': scheme_name,
        'score_given': score_given,
        'user': {
            'age'           : user_profile.get('age'),
            'annual_income' : user_profile.get('annual_income'),
            'gender'        : user_profile.get('gender'),
            'caste'         : user_profile.get('caste'),
            'state'         : user_profile.get('state'),
            'occupation'    : user_profile.get('occupation'),
        }
    }

    interactions = load_interactions()
    interactions.append(entry)
    save_interactions(interactions)
    return entry

# ── Get interaction summary per scheme ────────────────────────
def get_scheme_interaction_counts():
    """
    Returns a dict: { scheme_slug: total_weighted_interactions }
    Used by the learning layer to compute popularity boost.
    """
    interactions = load_interactions()
    counts = {}
    for entry in interactions:
        slug   = entry.get('scheme_slug', '')
        weight = entry.get('action_weight', 1)
        counts[slug] = counts.get(slug, 0) + weight
    return counts

# ── Get interactions filtered by similar users ────────────────
def get_similar_user_interactions(user_profile, max_age_diff=10, max_income_ratio=2.0):
    """
    Returns scheme interaction counts only from users with similar profiles.
    'Similar' means: same state + same occupation + age within range.

    This makes the popularity boost relevant — a scheme popular with
    farmers in Maharashtra should boost MORE for another Maharashtra farmer,
    not for a student in Kerala.
    """
    interactions = load_interactions()
    u_state  = user_profile.get('state', '').strip().lower()
    u_occ    = user_profile.get('occupation', '').strip().lower()
    u_age    = user_profile.get('age', 0) or 0
    u_income = user_profile.get('annual_income', 0) or 0

    counts = {}
    for entry in interactions:
        eu = entry.get('user', {})
        e_state  = (eu.get('state') or '').strip().lower()
        e_occ    = (eu.get('occupation') or '').strip().lower()
        e_age    = eu.get('age') or 0
        e_income = eu.get('annual_income') or 0

        # Similarity checks
        state_match  = (e_state == u_state) or not u_state
        occ_match    = (e_occ == u_occ) or not u_occ
        age_match    = abs(e_age - u_age) <= max_age_diff
        income_match = True
        if u_income > 0 and e_income > 0:
            ratio = max(u_income, e_income) / min(u_income, e_income)
            income_match = ratio <= max_income_ratio

        # Must match state + occupation at minimum
        if state_match and occ_match and age_match and income_match:
            slug   = entry.get('scheme_slug', '')
            weight = entry.get('action_weight', 1)
            counts[slug] = counts.get(slug, 0) + weight

    return counts

# ── Stats helper ───────────────────────────────────────────────
def get_stats():
    """Print a summary of all logged interactions."""
    interactions = load_interactions()
    total = len(interactions)

    if total == 0:
        return {"total": 0, "by_action": {}, "top_schemes": []}

    by_action = {}
    scheme_counts = {}
    for entry in interactions:
        action = entry.get('action', 'unknown')
        by_action[action] = by_action.get(action, 0) + 1
        slug = entry.get('scheme_slug', '')
        name = entry.get('scheme_name', '')[:50]
        scheme_counts[slug] = scheme_counts.get(slug, {'name': name, 'count': 0})
        scheme_counts[slug]['count'] += entry.get('action_weight', 1)

    top_schemes = sorted(scheme_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:5]

    return {
        "total"      : total,
        "by_action"  : by_action,
        "top_schemes": [(slug, info['name'], info['count']) for slug, info in top_schemes]
    }


# ══════════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("Testing interaction logger...\n")

    # Simulate 3 users interacting with schemes
    users = [
        {'age': 32, 'annual_income': 80000,  'gender': 'male',   'caste': 'SC',      'state': 'Maharashtra', 'occupation': 'farmer'},
        {'age': 28, 'annual_income': 70000,  'gender': 'male',   'caste': 'SC',      'state': 'Maharashtra', 'occupation': 'farmer'},
        {'age': 24, 'annual_income': 60000,  'gender': 'female', 'caste': 'OBC',     'state': 'Rajasthan',   'occupation': 'student'},
    ]

    interactions_to_log = [
        (users[0], 'pm-kisan', 'PM-KISAN', 'view',   75.0),
        (users[0], 'pm-kisan', 'PM-KISAN', 'select', 75.0),
        (users[0], 'kcc',      'Kisan Credit Card', 'view', 70.0),
        (users[1], 'pm-kisan', 'PM-KISAN', 'apply',  78.0),
        (users[1], 'kcc',      'Kisan Credit Card', 'select', 71.0),
        (users[2], 'nsp',      'National Scholarship Portal', 'view',   80.0),
        (users[2], 'nsp',      'National Scholarship Portal', 'apply',  80.0),
    ]

    for user, slug, name, action, score in interactions_to_log:
        log_interaction(user, slug, name, action, score)
        print(f"  Logged: {action:6} | {name[:35]} | User:{user['state']}/{user['occupation']}")

    print("\n--- Interaction Stats ---")
    stats = get_stats()
    print(f"Total logs  : {stats['total']}")
    print(f"By action   : {stats['by_action']}")
    print(f"Top schemes :")
    for slug, name, count in stats['top_schemes']:
        print(f"  {slug:<20} | {name:<35} | weighted count: {count}")

    print("\n--- Similar user filter (Maharashtra farmer) ---")
    similar_counts = get_similar_user_interactions(users[0])
    print(f"Schemes from similar users: {similar_counts}")
