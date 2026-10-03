"""
Step 3 — Scoring & Ranking Engine
===================================
Takes eligible schemes (output of eligibility_engine) and scores each one.
Returns top N ranked schemes for the user.

Scoring logic — each scheme gets points across 6 dimensions:

  1. STATE MATCH         (0-25 pts)  — state-specific scheme scores higher than national
  2. OCCUPATION MATCH    (0-25 pts)  — exact occupation match scores highest
  3. CASTE MATCH         (0-20 pts)  — specific caste targeting scores higher than open
  4. INCOME PROXIMITY    (0-15 pts)  — the closer user income is to the limit, the higher
  5. BENEFIT AMOUNT      (0-10 pts)  — higher benefit amount scores higher (normalised)
  6. AGE PROXIMITY       (0-5  pts)  — how well age fits within the range

  Total max = 100 pts (base score)

  Dynamic boost: schemes that have been chosen more by similar users
  get an additional popularity boost (added in Step 5).

Weights are stored in a JSON file so the learning layer can update them.
"""

import os
import json

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE = os.path.join(BASE_DIR, 'model_weights.json')

# ── Default weights ────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "state_match"       : 25,
    "occupation_match"  : 25,
    "caste_match"       : 20,
    "income_proximity"  : 15,
    "benefit_amount"    : 10,
    "age_proximity"     : 5,
}

def load_weights():
    """Load weights from file if it exists, else use defaults."""
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r') as f:
            saved = json.load(f)
        # Merge with defaults in case new keys were added
        weights = DEFAULT_WEIGHTS.copy()
        weights.update(saved.get('weights', {}))
        return weights
    return DEFAULT_WEIGHTS.copy()

def save_weights(weights):
    """Persist weights to JSON file."""
    data = {}
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r') as f:
            data = json.load(f)
    data['weights'] = weights
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ── Helper ─────────────────────────────────────────────────────
def to_float(val):
    try:
        v = float(val)
        return v if v == v else None
    except (ValueError, TypeError):
        return None

# ── Individual scoring functions ───────────────────────────────

def score_state(scheme, user, weight):
    """
    State-specific scheme = full weight.
    National (level=Central or state='all') = half weight.
    """
    s_level = scheme.get('level', '').strip().lower()
    s_state = scheme.get('state_name', 'all').strip().lower()
    u_state = user.get('state', '').strip().lower()

    if s_level == 'central' or s_state in ('all', '', 'nan'):
        return weight * 0.5   # national scheme — less personalised

    s_state_list = [s.strip().lower() for s in s_state.split(',')]
    if u_state in s_state_list:
        return weight * 1.0   # exact state match

    return weight * 0.3       # state exists but doesn't match (shouldn't happen after filter)


def score_occupation(scheme, user, weight):
    """
    Exact occupation match = full weight.
    Scheme is 'any' = half weight (generic scheme).
    """
    s_occ = scheme.get('occupation', 'any').strip().lower()
    u_occ = user.get('occupation', '').strip().lower()

    if s_occ in ('any', '', 'nan'):
        return weight * 0.5   # open to all occupations

    s_occ_list = [o.strip() for o in s_occ.split(',')]
    if u_occ in s_occ_list:
        return weight * 1.0   # exact match

    return weight * 0.0       # no match (filtered out already, safety fallback)


def score_caste(scheme, user, weight):
    """
    Scheme targets user's specific caste = full weight.
    Scheme is open to all castes = half weight.
    """
    s_caste = scheme.get('caste_category', 'all').strip()
    u_caste = user.get('caste', '').strip()

    if s_caste in ('all', '', 'nan'):
        return weight * 0.5

    s_caste_list = [c.strip() for c in s_caste.split(',')]
    if u_caste in s_caste_list:
        return weight * 1.0

    return weight * 0.0


def score_income_proximity(scheme, user, weight):
    """
    If user income is close to the limit (within 80%) — high score.
    If scheme has no income limit — half weight.
    Formula: score = weight * (1 - gap_ratio)
    """
    s_max_income = to_float(scheme.get('max_income_inr'))
    u_income     = user.get('annual_income')

    if s_max_income is None or u_income is None:
        return weight * 0.5   # no income data — neutral

    # User income must be <= max (guaranteed by eligibility filter)
    # Proximity: 0 gap = full score, large gap = lower score
    gap_ratio = (s_max_income - u_income) / s_max_income
    # Closer to limit = more targeted for this user
    proximity = max(0.0, 1.0 - gap_ratio)
    return weight * proximity


def score_benefit_amount(scheme, all_schemes_max_benefit, weight):
    """
    Normalise benefit amount across all schemes.
    Higher benefit = higher score.
    """
    s_benefit = to_float(scheme.get('benefit_amount_inr'))

    if s_benefit is None or all_schemes_max_benefit is None or all_schemes_max_benefit == 0:
        return weight * 0.3   # unknown benefit — low but not zero

    normalised = min(s_benefit / all_schemes_max_benefit, 1.0)
    return weight * normalised


def score_age_proximity(scheme, user, weight):
    """
    How well does the user's age fit the scheme's age range.
    Centred in range = full score. Near edge = partial.
    No age restriction = half weight.
    """
    s_min = to_float(scheme.get('min_age'))
    s_max = to_float(scheme.get('max_age'))
    u_age = user.get('age')

    if u_age is None:
        return weight * 0.5

    if s_min is None and s_max is None:
        return weight * 0.5   # no restriction

    if s_min is not None and s_max is not None:
        age_range  = s_max - s_min
        if age_range <= 0:
            return weight * 0.5
        midpoint   = (s_min + s_max) / 2
        distance   = abs(u_age - midpoint)
        proximity  = max(0.0, 1.0 - (distance / (age_range / 2)))
        return weight * proximity

    # Only one bound
    if s_min is not None:
        # Closer to min = more eligible feel
        diff = u_age - s_min
        proximity = min(diff / 20.0, 1.0) if diff >= 0 else 0.0
        return weight * proximity

    if s_max is not None:
        diff = s_max - u_age
        proximity = min(diff / 20.0, 1.0) if diff >= 0 else 0.0
        return weight * proximity

    return weight * 0.5


# ── Main scoring function ──────────────────────────────────────
def score_scheme(scheme, user, weights, max_benefit):
    """Compute total score for a single scheme given a user profile."""
    total = 0.0
    total += score_state(scheme, user, weights['state_match'])
    total += score_occupation(scheme, user, weights['occupation_match'])
    total += score_caste(scheme, user, weights['caste_match'])
    total += score_income_proximity(scheme, user, weights['income_proximity'])
    total += score_benefit_amount(scheme, max_benefit, weights['benefit_amount'])
    total += score_age_proximity(scheme, user, weights['age_proximity'])
    return round(total, 4)


# ── Rank eligible schemes ──────────────────────────────────────
def rank_schemes(eligible_schemes, user, top_n=5, popularity_boost=None):
    """
    Score and rank all eligible schemes for a user.

    Args:
        eligible_schemes : list of scheme dicts (from eligibility_engine)
        user             : user profile dict
        top_n            : number of top results to return
        popularity_boost : dict {scheme_slug: boost_score} from learning layer

    Returns:
        list of (scheme, score) tuples, sorted by score descending
    """
    weights = load_weights()

    # Find max benefit across eligible schemes for normalisation
    benefits = [to_float(s.get('benefit_amount_inr')) for s in eligible_schemes]
    benefits = [b for b in benefits if b is not None]
    max_benefit = max(benefits) if benefits else 1.0

    scored = []
    for scheme in eligible_schemes:
        base_score = score_scheme(scheme, user, weights, max_benefit)

        # Add popularity boost from learning layer (Step 5)
        boost = 0.0
        if popularity_boost:
            slug  = scheme.get('slug', '')
            boost = popularity_boost.get(slug, 0.0)

        final_score = base_score + boost
        scored.append((scheme, round(final_score, 4)))

    # Sort descending by score
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


# ══════════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    from eligibility_engine import load_schemes, get_eligible_schemes

    print("Loading schemes...")
    all_schemes = load_schemes()

    test_users = [
        {
            'name': 'Ramesh', 'age': 32, 'annual_income': 80000,
            'gender': 'male', 'caste': 'SC',
            'state': 'Maharashtra', 'occupation': 'farmer',
        },
        {
            'name': 'Priya', 'age': 24, 'annual_income': 60000,
            'gender': 'female', 'caste': 'OBC',
            'state': 'Rajasthan', 'occupation': 'student',
        },
        {
            'name': 'Suresh', 'age': 45, 'annual_income': 200000,
            'gender': 'male', 'caste': 'General',
            'state': 'Gujarat', 'occupation': 'entrepreneur',
        },
    ]

    print('=' * 65)
    for user in test_users:
        eligible = get_eligible_schemes(user, all_schemes)
        ranked   = rank_schemes(eligible, user, top_n=5)

        print(f"\nUser : {user['name']} | {user['state']} | "
              f"{user['caste']} | {user['occupation']} | "
              f"Age:{user['age']} | Income:₹{user['annual_income']:,}")
        print(f"Eligible: {len(eligible)} schemes → Top 5 after ranking:\n")

        for i, (scheme, score) in enumerate(ranked, 1):
            benefit = to_float(scheme.get('benefit_amount_inr'))
            benefit_str = f"₹{int(benefit):,}" if benefit else "N/A"
            print(f"  {i}. [{score:5.1f} pts] {scheme['scheme_name'][:60]}")
            print(f"       State:{scheme['state_name'][:20]} | "
                  f"Occ:{scheme['occupation'][:20]} | "
                  f"Benefit:{benefit_str}")
        print('-' * 65)
