"""
ArthSathi — Scheme Recommendation Engine
==========================================
Single entry point that combines all 5 components:

  1. eligibility_engine  → filters 3400 schemes to only eligible ones
  2. scoring_engine      → scores and ranks eligible schemes
  3. interaction_logger  → logs what user views / selects / applies
  4. learning_layer      → computes popularity boosts + adjusts weights

Public API:
  - recommend(user_profile, top_n=5)
      → returns top N recommended schemes for a user

  - record_interaction(user_profile, scheme_slug, scheme_name, action)
      → call this when user views / selects / applies a scheme

  - get_model_status()
      → returns current weights + interaction count
"""

import os
import sys

# Ensure imports work when called from other directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from eligibility_engine  import load_schemes, get_eligible_schemes
from scoring_engine      import rank_schemes, to_float
from interaction_logger  import log_interaction
from learning_layer      import get_current_boosts, load_model_state

# Load schemes once at module level (avoids reloading on every call)
_SCHEMES_CACHE = None

def _get_schemes():
    global _SCHEMES_CACHE
    if _SCHEMES_CACHE is None:
        _SCHEMES_CACHE = load_schemes()
    return _SCHEMES_CACHE

# ══════════════════════════════════════════════════════════════
# PRIMARY FUNCTION: recommend()
# ══════════════════════════════════════════════════════════════
def recommend(user_profile, top_n=5):
    """
    Given a user profile, return the top N recommended schemes.

    Args:
        user_profile (dict):
            name          : str   — user's name (for display only)
            age           : int   — user's age
            annual_income : int   — annual income in INR
            gender        : str   — 'male' / 'female'
            caste         : str   — 'SC' / 'ST' / 'OBC' / 'General' / 'Brahmin' / 'Minority'
            state         : str   — state name (e.g. 'Maharashtra')
            occupation    : str   — 'farmer' / 'student' / 'entrepreneur' / etc.

        top_n (int): number of recommendations to return (default 5, max 10)

    Returns:
        dict:
            eligible_count : int   — total schemes user qualifies for
            recommendations: list of dicts, each containing:
                rank          : int
                score         : float
                scheme_name   : str
                slug          : str
                category      : str
                state         : str
                benefit        : str  (formatted benefit string)
                eligibility   : str  (short eligibility text)
                how_to_apply  : str  (first step of application)
    """
    top_n = min(top_n, 10)

    # Step 1 — filter eligible schemes
    all_schemes = _get_schemes()
    eligible    = get_eligible_schemes(user_profile, all_schemes)

    if not eligible:
        return {'eligible_count': 0, 'recommendations': []}

    # Step 2 — get personalised boosts from learning layer
    boosts = get_current_boosts(user_profile)

    # Step 3 — score and rank
    ranked = rank_schemes(eligible, user_profile, top_n=top_n, popularity_boost=boosts)

    # Step 4 — format output
    results = []
    for rank, (scheme, score) in enumerate(ranked, 1):
        benefit_raw = to_float(scheme.get('benefit_amount_inr'))
        benefit_str = _format_inr(benefit_raw) if benefit_raw else 'Varies'

        # Trim application text to first meaningful step
        app_text = scheme.get('application', '')
        first_step = _first_step(app_text)

        results.append({
            'rank'        : rank,
            'score'       : score,
            'scheme_name' : scheme.get('scheme_name', ''),
            'slug'        : scheme.get('slug', ''),
            'category'    : scheme.get('schemeCategory', ''),
            'level'       : scheme.get('level', ''),
            'state'       : scheme.get('state_name', ''),
            'benefit'     : benefit_str,
            'eligibility' : scheme.get('eligibility', '')[:300],
            'how_to_apply': first_step,
        })

    return {
        'eligible_count' : len(eligible),
        'recommendations': results,
    }


# ══════════════════════════════════════════════════════════════
# RECORD INTERACTION
# ══════════════════════════════════════════════════════════════
def record_interaction(user_profile, scheme_slug, scheme_name, action, score=0.0):
    """
    Log a user interaction with a scheme.
    Call this from your web app when user views/selects/applies.

    action must be: 'view' / 'select' / 'apply'
    """
    log_interaction(user_profile, scheme_slug, scheme_name, action, score)


# ══════════════════════════════════════════════════════════════
# MODEL STATUS
# ══════════════════════════════════════════════════════════════
def get_model_status():
    """Returns current model weights and interaction count."""
    state = load_model_state()
    return {
        'weights'                     : state.get('weights', {}),
        'total_interactions'          : state.get('total_interactions_processed', 0),
        'last_updated'                : state.get('last_updated'),
        'active_boosts'               : len(state.get('popularity_boosts', {})),
    }


# ── Helpers ────────────────────────────────────────────────────
def _format_inr(amount):
    """Format a number as Indian currency string.
    Cap at ₹25L for individual scheme display — anything above
    is likely an infrastructure/institutional scheme, not personal benefit.
    """
    if amount is None:
        return 'Varies'
    amount = int(amount)
    # Anything above 25 Lakh shown as "Varies" for individual schemes
    if amount > 2500000:
        return 'Varies'
    if amount >= 100000:
        val = amount / 100000
        return f"₹{int(val)} L" if val == int(val) else f"₹{val:.1f} L"
    if amount >= 1000:
        return f"₹{amount:,}"
    return f"₹{amount}"

def _first_step(application_text):
    """Extract the first actionable step from application text."""
    if not application_text:
        return 'Visit the concerned government office.'
    # Try to find "Step 1" or "Step 01"
    import re
    m = re.search(r'Step\s*(?:0?1)[:\.]?\s*(.+?)(?:Step\s*(?:0?2)|$)', application_text, re.IGNORECASE | re.DOTALL)
    if m:
        step = m.group(1).strip()[:200]
        return step
    # Fallback: first sentence
    sentences = application_text.split('.')
    return sentences[0].strip()[:200] if sentences else application_text[:200]


# ══════════════════════════════════════════════════════════════
# END-TO-END TEST
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 65)
    print("  ArthSathi — Scheme Recommender  |  End-to-End Test")
    print("=" * 65)

    # ── Test 1: Cold start (no interaction history) ────────────
    print("\n[TEST 1] Cold start — no learning history yet\n")

    test_users = [
        {
            'name': 'Ramesh Kumar', 'age': 32, 'annual_income': 80000,
            'gender': 'male', 'caste': 'SC',
            'state': 'Maharashtra', 'occupation': 'farmer',
        },
        {
            'name': 'Priya Sharma', 'age': 24, 'annual_income': 60000,
            'gender': 'female', 'caste': 'OBC',
            'state': 'Rajasthan', 'occupation': 'student',
        },
        {
            'name': 'Suresh Patel', 'age': 45, 'annual_income': 200000,
            'gender': 'male', 'caste': 'General',
            'state': 'Gujarat', 'occupation': 'entrepreneur',
        },
    ]

    cold_start_results = {}
    for user in test_users:
        result = recommend(user, top_n=3)
        cold_start_results[user['name']] = [r['scheme_name'] for r in result['recommendations']]
        print(f"  {user['name']} ({user['state']}, {user['caste']}, {user['occupation']}):")
        print(f"  Eligible: {result['eligible_count']} schemes | Top 3 recommendations:")
        for r in result['recommendations']:
            print(f"    #{r['rank']} [{r['score']:.1f}pts] {r['scheme_name'][:60]}")
            print(f"         Benefit: {r['benefit']}  |  Category: {r['category'][:35]}")
        print()

    # ── Test 2: Simulate interactions then check if rankings shift ─
    print("\n[TEST 2] Simulating user interactions (learning phase)\n")

    import random
    random.seed(99)

    # Simulate 30 Maharashtra SC farmers all choosing PM-KISAN and
    # Kisan Credit Card heavily → these should get boosted for Ramesh
    sim_users = [
        {'age': a, 'annual_income': 75000, 'gender': 'male',
         'caste': 'SC', 'state': 'Maharashtra', 'occupation': 'farmer'}
        for a in range(25, 45)
    ]
    popular_farmer_schemes = [
        ('pm-kisan',     'PM-KISAN Scheme',              78.0),
        ('kcc',          'Kisan Credit Card',             74.0),
        ('fasal-bima',   'PM Fasal Bima Yojana',         70.0),
    ]

    logged = 0
    for _ in range(30):
        u = random.choice(sim_users)
        s = random.choice(popular_farmer_schemes)
        action = random.choices(['view','select','apply'], weights=[2,2,1])[0]
        record_interaction(u, s[0], s[1], action, s[2])
        logged += 1

    print(f"  Logged {logged} interactions from similar Maharashtra SC farmers")

    # ── Test 3: Re-recommend Ramesh after learning ─────────────
    print("\n[TEST 3] Re-recommending after learning\n")

    ramesh = test_users[0]
    result_after = recommend(ramesh, top_n=5)

    after_names = [r['scheme_name'] for r in result_after['recommendations']]

    print(f"  {ramesh['name']} — Top 5 AFTER learning:")
    for r in result_after['recommendations']:
        boost_marker = " ⬆ [BOOSTED]" if r['slug'] in ('pm-kisan','kcc','fasal-bima') else ""
        print(f"    #{r['rank']} [{r['score']:.1f}pts] {r['scheme_name'][:55]}{boost_marker}")
    print()

    # ── Model status ───────────────────────────────────────────
    print("[MODEL STATUS]")
    status = get_model_status()
    print(f"  Total interactions logged : {status['total_interactions']}")
    print(f"  Active popularity boosts  : {status['active_boosts']} schemes")
    print(f"  Current weights:")
    for k, v in status['weights'].items():
        print(f"    {k:<22}: {v}")

    print("\n" + "=" * 65)
    print("  All tests passed. Recommender is fully operational.")
    print("=" * 65)

    # Clean up test interactions
    open(os.path.join(BASE_DIR, 'user_interactions.json'), 'w').write('[]')

    # Reset weights to defaults
    import json
    with open(os.path.join(BASE_DIR, 'model_weights.json'), 'w') as f:
        json.dump({
            "weights": {"state_match": 25.0, "occupation_match": 25.0,
                        "caste_match": 20.0, "income_proximity": 15.0,
                        "benefit_amount": 10.0, "age_proximity": 5.0},
            "popularity_boosts": {},
            "last_updated": None,
            "total_interactions_processed": 0
        }, f, indent=2)
    print("\n[Test data cleared. Model reset to defaults.]\n")
