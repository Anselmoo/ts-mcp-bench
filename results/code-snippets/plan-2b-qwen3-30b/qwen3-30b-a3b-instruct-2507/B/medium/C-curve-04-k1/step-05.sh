python3 -c "
# Given parameters
B = 800  # cm⁻¹
C = 3473  # cm⁻¹

# Dq/B values to analyze
dq_over_b_values = [1.45, 2.55, 3.25]

# For octahedral d5, the ground term is 6S
# Excited terms: 4G, 4P, 2G, 2H, 2F, 2D, 2P
# The correct energy expressions in units of Dq, B, and C are:
# 4G: E = 10*Dq + 15*B + 10*C
# 4P: E = 10*Dq + 15*B + 20*C
# 2G: E = 10*Dq + 15*B + 10*C
# 2H: E = 10*Dq + 15*B + 15*C
# 2F: E = 10*Dq + 15*B + 20*C
# 2D: E = 10*Dq + 15*B + 20*C
# 2P: E = 10*Dq + 15*B + 20*C

# Calculate E/B for each term at each Dq/B value
results = []
for dq_over_b in dq_over_b_values:
    Dq = dq_over_b * B
    # Calculate E for each term
    E_4G = 10*Dq + 15*B + 10*C
    E_4P = 10*Dq + 15*B + 20*C
    E_2G = 10*Dq + 15*B + 10*C
    E_2H = 10*Dq + 15*B + 15*C
    E_2F = 10*Dq + 15*B + 20*C
    E_2D = 10*Dq + 15*B + 20*C
    E_2P = 10*Dq + 15*B + 20*C
    
    # Calculate E/B
    E_4G_over_B = E_4G / B
    E_4P_over_B = E_4P / B
    E_2G_over_B = E_2G / B
    E_2H_over_B = E_2H / B
    E_2F_over_B = E_2F / B
    E_2D_over_B = E_2D / B
    E_2P_over_B = E_2P / B
    
    # Create list of terms with E/B
    terms = [
        ("4G", E_4G_over_B),
        ("4P", E_4P_over_B),
        ("2G", E_2G_over_B),
        ("2H", E_2H_over_B),
        ("2F", E_2F_over_B),
        ("2D", E_2D_over_B),
        ("2P", E_2P_over_B)
    ]
    
    # Sort by energy
    terms.sort(key=lambda x: x[1])
    
    # Take first three
    top3 = terms[:3]
    
    # Append to results
    for term, e_over_b in top3:
        results.append({
            "dq_over_b": dq_over_b,
            "term": term,
            "e_over_b": e_over_b
        })

# Output results
for r in results:
    print(f"{r['dq_over_b']}, {r['term']}, {r['e_over_b']:.2f}")
"