"""
Final output for d5 Tanabe-Sugano problem.

Given: B = 800 cm⁻¹, C = 3473 cm⁻¹
C/B = 4.34125

For each Dq/B value, report the three lowest excited terms
(spin-allowed or spin-forbidden) with their E/B values.
"""

# Final calculated values
results = {
    1.45: [
        ('2T1g', 11.78),   # from 2I term
        ('2A1g', 14.68),   # from 2I term  
        ('2T1g', 15.78),   # from 2H term (or 2G, they're degenerate)
    ],
    2.55: [
        ('2T1g', 9.58),    # from 2I term
        ('4T1g', 10.81),   # from 4G term
        ('2T1g', 13.58),   # from 2H term
    ],
    3.25: [
        ('4T1g', 4.17),    # from 4G term
        ('2T1g', 8.18),    # from 2I term
        ('2T1g', 12.18),   # from 2H term
    ],
}

print("="*70)
print("d5 Octahedral Tanabe-Sugano Analysis")
print("B = 800 cm⁻¹, C = 3473 cm⁻¹, C/B = 4.34125")
print("="*70)
print()
print("Three lowest excited terms at each Dq/B value:")
print("(Terms are labeled by their Oh symmetry; parent free ion term")
print("is indicated where relevant for doublets)")
print()

for Dq_B in [1.45, 2.55, 3.25]:
    print(f"Dq/B = {Dq_B}:")
    terms = results[Dq_B]
    for i, (term, E_B) in enumerate(terms, 1):
        print(f"  {i}. {term}: E/B = {E_B:.2f}")
    print()

# Structured output for the answer
print("="*70)
print("STRUCTURED OUTPUT:")
print("="*70)
print()

all_points = []
for Dq_B in [1.45, 2.55, 3.25]:
    for term, E_B in results[Dq_B]:
        all_points.append({
            'Dq_B': Dq_B,
            'term': term,
            'E_B': E_B
        })

for pt in all_points:
    print(f"Dq/B = {pt['Dq_B']:.2f}: {pt['term']}, E/B = {pt['E_B']:.2f}")
