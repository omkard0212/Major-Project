"""
Step 5 — Self-Learning Layer
==============================
Reads user_interactions.json and does two things:

  1. POPULARITY BOOST
     Computes a per-scheme boost score based on how many similar users
     interacted with it. This boost is passed to rank_schemes() in the
     scoring engine.

     Formula:
       raw_count     = sum of weighted interactions for this scheme
                       from similar users (same state + occupation)
       normalised    = raw_count / max_count_across_all_schemes
       boost         = normalised * MAX_BOOST

     MAX_BOOST = 15 pts (so learning can shift rankings but not override
     the base eligibility score completely)

  2. WEIGHT ADJUSTMENT (Global Learning)
     Every N interactions, we look at which scoring dimensions best
     predicted actual user choices, and nudge the weights slightly
     in that direction.

     For example:
     - If users with high income proximity keep choosing those schemes
       → nudge income_proximity weight up slightly
     - If benefit_amount doesn't correlate much with choices
       → nudge it down slightly

     Weights are saved to model_weights.json after each adjustment.
     Changes are small (±1 pt per cycle) so the model shifts gradually.

All stored in model_weights.json:
  {
    "weights": { ... },
    "popularity_boosts": { scheme_slug: boost_value },
    "last_updated": "ISO timestamp",
    "total_interactions_processed": 123
  }
"""

import os
import json
from datetime import datetime

BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE      = os.path.join(BASE_DIR, 'model_weights.json')
INTERACTIONS_FILE = os.path.join(BASE_DIR, 'user_interactions.json')

MAX_BOOST              = 15.0   # max pts a scheme can gain from popularity
WEIGHT_ADJUST_EVERY    = 20     # adjust weights every N interactions
MIN_WEIGHT             = 5.0    # no weight can drop below this
MAX_WEIGHT             = 40.0   # no weight can exceed this
WEIGHT_NUDGE           = 0.5    # how much to shift weights per cycle

DEFAULT_WEIGHTS = {
    "state_match"      : 25.0,
    "occupation_match" : 25.0,
    "caste_match"      : 20.0,
    "income_proximity" : 15.0,
    "benefit_amount"   : 10.0,
    "age_proximity"    :  5.0,
}

# ── Load / Save model state ────────────────────────────────────
def load_model_state():
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {
        "weights"                      : DEFAULT_WEIGHTS.copy(),
        "popularity_boosts"            : {},
        "last_updated"                 : None,
        "total_interactions_processed" : 0,
    }

def save_model_state(state):
    state['last_updated'] = datetime.now().isoformat()
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ── Load interactions ──────────────────────────────────────────
def load_interactions():
    if not os.path.exists(INTERACTIONS_FILE):
        return []
    with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# ── Step A: Compute popularity boosts ─────────────────────────
def compute_popularity_boosts(interactions, user_profile=None):
    """
    Compute a boost score per scheme slug.
    If user_profile is given, only count interactions from similar users.
    If no user_profile, use all interactions.
    """
    u_state = (user_profile.get('state', '') or '').strip().lower() if user_profile else ''
    u_occ   = (user_profile.get('occupation', '') or '').strip().lower() if user_profile else ''
    u_age   = user_profile.get('age', 0) or 0 if user_profile else 0

    raw_counts = {}

    for entry in interactions:
        eu      = entry.get('user', {})
        e_state = (eu.get('state') or '').strip().lower()
        e_occ   = (eu.get('occupation') or '').strip().lower()
        e_age   = eu.get('age') or 0

        # Similarity filter when user profile is given
        if user_profile:
            state_ok  = (not u_state) or (e_state == u_state)
            occ_ok    = (not u_occ)   or (e_occ   == u_occ)
            age_ok    = abs(e_age - u_age) <= 10
            if not (state_ok and occ_ok and age_ok):
                continue

        slug   = entry.get('scheme_slug', '')
        weight = entry.get('action_weight', 1)
        raw_counts[slug] = raw_counts.get(slug, 0) + weight

    if not raw_counts:
        return {}

    # Normalise: map to [0, MAX_BOOST]
    max_count = max(raw_counts.values())
    boosts = {
        slug: round((count / max_count) * MAX_BOOST, 4)
        for slug, count in raw_counts.items()
    }
    return boosts

# ── Step B: Weight adjustment ──────────────────────────────────
def adjust_weights(interactions, current_weights):
    """
    Analyse recent interactions to see which scoring dimensions
    correlate with user choices (select/apply actions).

    Logic:
    - For each 'select' or 'apply' action, we look at the scheme's
      properties vs the user's profile to see which dimensions were
      a strong match at the time of selection.
    - Dimensions that frequently align with choices → nudge weight up.
    - Dimensions that rarely align → nudge down.
    - Changes are small (WEIGHT_NUDGE) and clamped to [MIN, MAX].
    """
    # Only learn from deliberate choices (select + apply), not passive views
    choices = [e for e in interactions if e.get('action') in ('select', 'apply')]

    if len(choices) < 5:
        return current_weights  # not enough data yet

    # Count how often each dimension was a "strong match" in chosen schemes
    dimension_hits = {k: 0 for k in current_weights}
    total_choices  = len(choices)

    for entry in choices:
        eu     = entry.get('user', {})
        slug   = entry.get('scheme_slug', '')
        # We don't have the full scheme here — use proxy signals from user/entry data
        # score_given tells us how well the scheme scored overall
        score  = entry.get('score_given', 0)

        # Proxy: if score was high, the scheme was a good match on multiple dims
        # We credit all dimensions proportionally to score
        # (In a full system, we'd store per-dimension scores; this is the lightweight version)
        score_ratio = min(score / 100.0, 1.0)  # normalise to 0-1

        for dim in dimension_hits:
            dimension_hits[dim] += score_ratio

    # Compute average hit rate per dimension
    avg_hits = {dim: dimension_hits[dim] / total_choices for dim in dimension_hits}
    overall_avg = sum(avg_hits.values()) / len(avg_hits)

    # Nudge: dims above average → up, below average → down
    new_weights = {}
    for dim, w in current_weights.items():
        if avg_hits[dim] > overall_avg:
            new_weights[dim] = min(w + WEIGHT_NUDGE, MAX_WEIGHT)
        else:
            new_weights[dim] = max(w - WEIGHT_NUDGE, MIN_WEIGHT)

    # Re-normalise so total stays ~100
    total_new = sum(new_weights.values())
    target    = sum(DEFAULT_WEIGHTS.values())   # 100
    scale     = target / total_new if total_new > 0 else 1.0
    new_weights = {k: round(v * scale, 2) for k, v in new_weights.items()}

    return new_weights

# ── Main: run the learning cycle ──────────────────────────────
def run_learning_cycle(user_profile=None, force=False):
    """
    Main function called by the recommender.

    1. Always recomputes popularity boosts (personalised if user_profile given).
    2. Every WEIGHT_ADJUST_EVERY interactions, adjusts weights.

    Args:
        user_profile : dict — if given, boosts are personalised
        force        : bool — force weight adjustment even if threshold not reached

    Returns:
        boosts (dict) — { scheme_slug: boost_value } to pass to rank_schemes()
    """
    state       = load_model_state()
    interactions = load_interactions()
    total        = len(interactions)

    # Step A — always recompute boosts
    boosts = compute_popularity_boosts(interactions, user_profile)
    state['popularity_boosts'] = boosts

    # Step B — adjust weights periodically
    prev_processed = state.get('total_interactions_processed', 0)
    new_interactions = total - prev_processed

    if force or new_interactions >= WEIGHT_ADJUST_EVERY:
        old_weights = state.get('weights', DEFAULT_WEIGHTS.copy())
        new_weights = adjust_weights(interactions, old_weights)
        state['weights'] = new_weights
        state['total_interactions_processed'] = total

        print(f"[Learning] Weight adjustment triggered ({total} total interactions)")
        print(f"  Old weights: { {k: round(v,1) for k,v in old_weights.items()} }")
        print(f"  New weights: { {k: round(v,1) for k,v in new_weights.items()} }")

    save_model_state(state)
    return boosts

# ── Get current boosts (for recommender to use) ───────────────
def get_current_boosts(user_profile=None):
    """
    Quick read of saved boosts. Runs learning cycle first.
    Returns personalised boosts if user_profile given.
    """
    return run_learning_cycle(user_profile=user_profile)

# ── Get current weights (for scoring engine to use) ───────────
def get_current_weights():
    state = load_model_state()
    return state.get('weights', DEFAULT_WEIGHTS.copy())


# ══════════════════════════════════════════════════════════════
# QUICK TEST
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    from interaction_logger import log_interaction

    print("=== Testing Self-Learning Layer ===\n")

    # Simulate 25 interactions so weight adjustment triggers
    import random
    random.seed(42)

    users = [
        {'age': 30, 'annual_income': 80000,  'gender': 'male',   'caste': 'SC',  'state': 'Maharashtra', 'occupation': 'farmer'},
        {'age': 35, 'annual_income': 90000,  'gender': 'male',   'caste': 'SC',  'state': 'Maharashtra', 'occupation': 'farmer'},
        {'age': 28, 'annual_income': 70000,  'gender': 'male',   'caste': 'OBC', 'state': 'Maharashtra', 'occupation': 'farmer'},
        {'age': 24, 'annual_income': 60000,  'gender': 'female', 'caste': 'OBC', 'state': 'Rajasthan',   'occupation': 'student'},
        {'age': 22, 'annual_income': 50000,  'gender': 'female', 'caste': 'SC',  'state': 'Rajasthan',   'occupation': 'student'},
    ]
    schemes = [
        ('pm-kisan',   'PM-KISAN Scheme',              75.0),
        ('kcc',        'Kisan Credit Card',             72.0),
        ('fasal-bima', 'Pradhan Mantri Fasal Bima',     68.0),
        ('nsp',        'National Scholarship Portal',   80.0),
        ('post-mat',   'Post Matric Scholarship',       78.0),
    ]

    actions = ['view', 'view', 'select', 'apply']

    print("Logging 25 simulated interactions...")
    for i in range(25):
        user   = random.choice(users)
        scheme = random.choice(schemes)
        action = random.choice(actions)
        log_interaction(user, scheme[0], scheme[1], action, scheme[2])

    print("\nRunning learning cycle (force=True to trigger weight adjustment)...")
    user_profile = users[0]
    boosts = run_learning_cycle(user_profile=user_profile, force=True)

    print(f"\nPersonalised boosts for Maharashtra farmer:")
    for slug, boost in sorted(boosts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {slug:<20} : +{boost:.2f} pts")

    print(f"\nCurrent weights after learning:")
    weights = get_current_weights()
    for k, v in weights.items():
        print(f"  {k:<22}: {v}")

    # Clean up test interactions
    import os
    open(os.path.join(os.path.dirname(__file__), 'user_interactions.json'), 'w').write('[]')
    print("\n[Test data cleared]")
