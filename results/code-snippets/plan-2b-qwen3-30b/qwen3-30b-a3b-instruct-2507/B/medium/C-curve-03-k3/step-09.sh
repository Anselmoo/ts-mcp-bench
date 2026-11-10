python3 -c "# Constants
B = 784  # cm⁻¹

# Dq/B values
Dq_B_values = [1.45, 2.45, 3.00]

# Energy expressions in terms of Dq and B
# E/B = (3*Dq + 2*B)/B = 3*(Dq/B) + 2 for ⁴T₂g, ²Eg, ²T₂g, ²T₁g
# E/B = (6*Dq + 3*B)/B = 6*(Dq/B) + 3 for ⁴A₂g, ²A₁g

# Calculate E/B for each term at each Dq/B
results = []
for Dq_B in Dq_B_values:
    # ⁴T₂g, ²Eg, ²T₂g, ²T₁g: E/B = 3*Dq_B + 2
    e1 = 3*Dq_B + 2
    # ⁴A₂g, ²A₁g: E/B = 6*Dq_B + 3
    e2 = 6*Dq_B + 3
    # Collect all terms
    terms = [(e1, '⁴T₂g'), (e1, '²Eg'), (e1, '²T₂g'), (e1, '²T₁g'), (e2, '⁴A₂g'), (e2, '²A₁g')]
    # Sort by energy
    terms.sort()
    # Take the three lowest
    top3 = terms[:3]
    # Append to results
    for e_over_b, term in top3:
        results.append({'dq_over_b': Dq_B, 'term': term, 'e_over_b': e_over_b})

# Output results
for r in results:
    print(f'{{r[\'dq_over_b\']}}, {{r[\'term\']}}, {{r[\'e_over_b\']}}')"