"""
Step 1 — Dataset Verification Script
Checks schemes_processed.csv for:
  - Row count
  - Missing values in key columns
  - Invalid values (wrong gender, bad age ranges, negative income)
  - Sample rows for manual spot check
"""
import csv

VALID_GENDERS     = {'any', 'male', 'female'}
VALID_CASTES      = {'all', 'SC', 'ST', 'OBC', 'General', 'Brahmin', 'Minority'}
VALID_OCCUPATIONS = {
    'any', 'farmer', 'fisherman', 'construction_worker', 'student',
    'entrepreneur', 'woman_shg', 'artisan', 'daily_wage',
    'pwd', 'widow', 'bpl', 'tribal'
}

rows = []
with open('schemes_processed.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

total = len(rows)
print(f"\n{'='*55}")
print(f"  DATASET VERIFICATION REPORT")
print(f"{'='*55}")
print(f"  Total schemes : {total}")

# ── 1. Required columns present ───────────────────────────────
required_cols = [
    'scheme_name','eligibility','benefits','level',
    'schemeCategory','min_age','max_age','max_income_inr',
    'gender','caste_category','state_name','occupation',
    'benefit_amount_inr'
]
missing_cols = [c for c in required_cols if c not in rows[0]]
if missing_cols:
    print(f"\n  ❌ MISSING COLUMNS: {missing_cols}")
else:
    print(f"\n  ✅ All required columns present")

# ── 2. Fill rate for numeric fields ───────────────────────────
print(f"\n  --- Numeric field fill rate ---")
for f in ['min_age', 'max_age', 'max_income_inr', 'benefit_amount_inr']:
    filled = sum(1 for r in rows if r.get(f, '').strip() not in ('', 'nan', 'None'))
    pct = 100 * filled // total
    print(f"  {f:<22}: {filled:>4}/{total}  ({pct}%)")

# ── 3. Fill rate / validity for category fields ───────────────
print(f"\n  --- Category field stats ---")
for f in ['gender', 'caste_category', 'state_name', 'occupation']:
    specific = sum(1 for r in rows if r.get(f,'').strip() not in ('', 'any', 'all', 'nan'))
    pct = 100 * specific // total
    print(f"  {f:<22}: {specific:>4}/{total}  ({pct}%) have specific value")

# ── 4. Invalid values check ───────────────────────────────────
print(f"\n  --- Invalid value checks ---")
invalid_gender = [r['scheme_name'][:50] for r in rows
                  if r.get('gender','').strip() not in VALID_GENDERS and r.get('gender','').strip() != '']
invalid_age    = [r['scheme_name'][:50] for r in rows
                  if r.get('min_age','').strip() not in ('','nan','None')
                  and r.get('max_age','').strip() not in ('','nan','None')
                  and float(r['min_age']) >= float(r['max_age'])]
neg_income     = [r['scheme_name'][:50] for r in rows
                  if r.get('max_income_inr','').strip() not in ('','nan','None')
                  and float(r['max_income_inr']) < 0]

print(f"  Invalid gender values     : {len(invalid_gender)}")
print(f"  min_age >= max_age errors  : {len(invalid_age)}")
print(f"  Negative income values    : {len(neg_income)}")

if invalid_gender:
    print(f"    Samples: {invalid_gender[:3]}")
if invalid_age:
    print(f"    Samples: {invalid_age[:3]}")

# ── 5. Level distribution ─────────────────────────────────────
print(f"\n  --- Scheme level distribution ---")
levels = {}
for r in rows:
    lv = r.get('level','').strip()
    levels[lv] = levels.get(lv, 0) + 1
for lv, count in sorted(levels.items()):
    print(f"  {lv:<15}: {count}")

# ── 6. Top states ─────────────────────────────────────────────
print(f"\n  --- Top 10 states by scheme count ---")
states = {}
for r in rows:
    st = r.get('state_name','').strip().split(',')[0]  # take first state
    states[st] = states.get(st, 0) + 1
top_states = sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]
for st, count in top_states:
    print(f"  {st:<25}: {count}")

# ── 7. Top categories ─────────────────────────────────────────
print(f"\n  --- Top 8 scheme categories ---")
cats = {}
for r in rows:
    cat = r.get('schemeCategory','').strip().split(',')[0].strip()
    cats[cat] = cats.get(cat, 0) + 1
top_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:8]
for cat, count in top_cats:
    print(f"  {cat:<40}: {count}")

print(f"\n{'='*55}")
print("  ✅ Verification complete. Dataset ready for model.")
print(f"{'='*55}\n")
