import csv

rows = []
with open('schemes_processed.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 100:
            break
        rows.append({
            'row': i+1,
            'scheme_name': row['scheme_name'][:60],
            'eligibility': row['eligibility'][:300],
            'min_age':     row['min_age'],
            'max_age':     row['max_age'],
            'max_income':  row['max_income_inr'],
            'gender':      row['gender'],
            'caste':       row['caste_category'],
            'state':       row['state_name'],
            'occupation':  row['occupation'],
            'benefit':     row['benefit_amount_inr'],
        })

# Print as a readable report
print(f"{'#':<4} {'SCHEME':<45} {'AGE':<12} {'INCOME':<10} {'GENDER':<8} {'CASTE':<15} {'STATE':<20} {'OCC':<25} {'BENEFIT':<10}")
print("-"*160)
for r in rows:
    age_str = f"{r['min_age'] or '_'}-{r['max_age'] or '_'}"
    print(f"{r['row']:<4} {r['scheme_name']:<45} {age_str:<12} {r['max_income'] or '_':<10} {r['gender']:<8} {r['caste']:<15} {r['state']:<20} {r['occupation']:<25} {r['benefit'] or '_':<10}")
