python3 -c "
# Constants
B = 821  # cm^-1
C = 3657  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [0.90, 2.15, 3.35]

# Dq in cm^-1
Dq_values = [dq_over_b * B for dq_over_b in dq_over_b_values]

# Store results
results = []

for i, dq_over_b in enumerate(dq_over_b_values):
    Dq = Dq_values[i]
    # Compute E/B for each term
    E_5Eg = (10 * Dq) / B
    E_3T1gF = (15 * Dq + 2 * C) / B
    E_3T1gP = (20 * Dq + C) / B
    E_1Eg = (10 * Dq + 2 * C) / B
    E_1T2g = (15 * Dq) / B
    E_1T1g = (20 * Dq) / B
    
    # List all terms with their E/B
    terms = [
        ["5E_g", E_5Eg],
        ["3T_{1g}(F)", E_3T1gF],
        ["3T_{1g}(P)", E_3T1gP],
        ["1E_g", E_1Eg],
        ["1T_{2g}", E_1T2g],
        ["1T_{1g}", E_1T1g]
    ]
    
    # Sort by energy
    terms.sort(key=lambda x: x[1])
    
    # Take the three lowest
    top3 = terms[:3]
    
    # Append to results
    for term_label, e_over_b in top3:
        results.append({
            "dq_over_b": dq_over_b,
            "term": term_label,
            "e_over_b": e_over_b
        })

# Output results
for r in results:
    print(f"{r['dq_over_b']}, {r['term']}, {r['e_over_b']:.6f}")
"