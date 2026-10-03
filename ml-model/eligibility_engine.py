"""
Step 2 — Eligibility Matching Engine
=====================================
Takes a user profile and returns all schemes the user qualifies for.

User profile fields:
  - age          : int   (e.g. 28)
  - annual_income: int   (in INR, e.g. 120000)
  - gender       : str   ('male' / 'female')
  - caste        : str   ('SC' / 'ST' / 'OBC' / 'General' / 'Brahmin' / 'Minority')
  - state        : str   (e.g. 'Maharashtra')
  - occupation   : str   (e.g. 'farmer', 'student', 'entrepreneur' ...)

Matching rules:
  - age        : user age must be between scheme min_age and max_age
                 if min_age is blank → no lower limit
                 if max_age is blank → no upper limit
  - income     : user income must be <= scheme max_income_inr
                 if blank → no income restriction
  - gender     : scheme gender must be 'any' or match user gender
  - caste      : scheme caste must be 'all' or contain user's caste
  - state      : scheme state must be 'all' or match user's state
                 Central schemes always pass state check
  - occupation : scheme occupation must be 'any' or contain user's occupation
"""

import csv
import os

# Path to dataset — works from any directory
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATASET    = os.path.join(BASE_DIR, 'schemes_processed.csv')

# ── Load dataset once into memory ─────────────────────────────
def load_schemes():
    schemes = []
    with open(DATASET, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            schemes.append(row)
    return schemes

# ── Helper: safe float conversion ─────────────────────────────
def to_float(val):
    try:
        v = float(val)
        return v if v == v else None   # NaN check
    except (ValueError, TypeError):
        return None

# ── Core eligibility check for one scheme ─────────────────────
def is_eligible(scheme, user):
    """
    Returns True if the user profile passes all eligibility checks
    for the given scheme.
    """
    u_age    = user.get('age')
    u_income = user.get('annual_income')
    u_gender = (user.get('gender') or 'any').strip().lower()
    u_caste  = (user.get('caste')  or '').strip()
    u_state  = (user.get('state')  or '').strip().lower()
    u_occ    = (user.get('occupation') or '').strip().lower()

    # ── AGE CHECK ──────────────────────────────────────────────
    s_min_age = to_float(scheme.get('min_age'))
    s_max_age = to_float(scheme.get('max_age'))

    if s_min_age is not None and u_age is not None:
        if u_age < s_min_age:
            return False

    if s_max_age is not None and u_age is not None:
        if u_age > s_max_age:
            return False

    # ── INCOME CHECK ──────────────────────────────────────────
    s_max_income = to_float(scheme.get('max_income_inr'))

    if s_max_income is not None and u_income is not None:
        if u_income > s_max_income:
            return False

    # ── GENDER CHECK ──────────────────────────────────────────
    s_gender = scheme.get('gender', 'any').strip().lower()

    if s_gender not in ('any', '', 'nan'):
        if u_gender not in ('any', '') and u_gender != s_gender:
            return False

    # ── CASTE CHECK ───────────────────────────────────────────
    s_caste = scheme.get('caste_category', 'all').strip()

    if s_caste not in ('all', '', 'nan'):
        # scheme targets specific castes — user must be one of them
        s_caste_list = [c.strip() for c in s_caste.split(',')]
        if u_caste and u_caste not in s_caste_list:
            return False

    # ── STATE CHECK ───────────────────────────────────────────
    s_state = scheme.get('state_name', 'all').strip().lower()
    s_level = scheme.get('level', '').strip().lower()

    # Central schemes are available to everyone regardless of state
    if s_level == 'central':
        pass
    elif s_state not in ('all', '', 'nan'):
        s_state_list = [s.strip().lower() for s in s_state.split(',')]
        if u_state and u_state not in s_state_list:
            return False

    # ── OCCUPATION CHECK ──────────────────────────────────────
    s_occ = scheme.get('occupation', 'any').strip().lower()

    if s_occ not in ('any', '', 'nan'):
        s_occ_list = [o.strip() for o in s_occ.split(',')]
        if u_occ and u_occ not in s_occ_list:
            return False

    return True

# ── Main filter function ───────────────────────────────────────
def get_eligible_schemes(user_profile, schemes=None):
    """
    Filter all schemes for a given user profile.

    Args:
        user_profile (dict): user's details
        schemes (list): pre-loaded schemes list (optional, for performance)

    Returns:
        list of dicts — all schemes the user qualifies for
    """
    if schemes is None:
        schemes = load_schemes()

    eligible = [s for s in schemes if is_eligible(s, user_profile)]
    return eligible


# ══════════════════════════════════════════════════════════════
# QUICK TEST — run this file directly to verify
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("Loading schemes...")
    all_schemes = load_schemes()
    print(f"Loaded {len(all_schemes)} schemes.\n")

    # Test profiles
    test_users = [
        {
            'name'          : 'Ramesh',
            'age'           : 32,
            'annual_income' : 80000,
            'gender'        : 'male',
            'caste'         : 'SC',
            'state'         : 'Maharashtra',
            'occupation'    : 'farmer',
        },
        {
            'name'          : 'Priya',
            'age'           : 24,
            'annual_income' : 60000,
            'gender'        : 'female',
            'caste'         : 'OBC',
            'state'         : 'Rajasthan',
            'occupation'    : 'student',
        },
        {
            'name'          : 'Suresh',
            'age'           : 45,
            'annual_income' : 200000,
            'gender'        : 'male',
            'caste'         : 'General',
            'state'         : 'Gujarat',
            'occupation'    : 'entrepreneur',
        },
    ]

    print("=" * 60)
    for user in test_users:
        matched = get_eligible_schemes(user, all_schemes)
        print(f"User  : {user['name']} | Age:{user['age']} | "
              f"{user['gender']} | {user['caste']} | "
              f"{user['state']} | {user['occupation']} | "
              f"Income: ₹{user['annual_income']:,}")
        print(f"Matched schemes: {len(matched)}")
        print("Top 5 matches:")
        for s in matched[:5]:
            print(f"  - {s['scheme_name'][:70]}")
        print("-" * 60)
