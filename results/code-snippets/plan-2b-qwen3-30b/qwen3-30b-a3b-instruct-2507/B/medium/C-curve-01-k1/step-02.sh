python3 -c "
from scipy.constants import value as hbar

# Constants
B = 821  # cm^-1
C = 3657  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [0.90, 2.15, 3.35]

# d4 terms in octahedral field: 5E_g, 3T_{2g}, 3T_{1g}(F), 3T_{1g}(P), 1E_g, 1T_{2g}, 1T_{1g}
# Ground term is 3T_{2g} (for high-spin d4)
# We need energies of excited terms relative to ground term in units of B

# Energy expressions in units of B (using standard ligand field theory)
# E = (Dq/B) * (coefficients) + (C/B) * (coefficients) + (B) * (term energy in B)
# But we need to compute the actual energies from the term energies

# For d4, the term energies in cm^-1 (relative to ground term 3T_{2g}) are:
# 5E_g: 10Dq
# 3T_{1g}(F): 15Dq + 2C
# 3T_{1g}(P): 20Dq + C
# 1E_g: 10Dq + 2C
# 1T_{2g}: 15Dq
# 1T_{1g}: 20Dq

# But note: the 3T_{1g}(F) and 3T_{1g}(P) are not always the same; we must use the correct expressions
# Standard values from Tanabe-Sugano diagram for d4:
# 5E_g: 10Dq
# 3T_{1g}(F): 15Dq + 2C
# 3T_{1g}(P): 20Dq + C
# 1E_g: 10Dq + 2C
# 1T_{2g}: 15Dq
# 1T_{1g}: 20Dq

# But we must be careful: the 3T_{1g}(P) term is actually at 20Dq + C, and 3T_{1g}(F) at 15Dq + 2C
# And the 5E_g term is at 10Dq

# We will compute E/B = (E_cm1 / B) for each term, relative to ground term (3T_{2g})
# So E/B = (E_term - E_ground) / B
# E_ground = 0 (by definition)

# So E/B = E_term / B

# Convert Dq to cm^-1: Dq = (Dq/B) * B
Dq_values = [dq_over_b * B for dq_over_b in dq_over_b_values]

# Store results
results = []

for i, dq_over_b in enumerate(dq_over_b_values):
    Dq = Dq_values[i]
    # Terms in energy order for d4 (high-spin)
    # 5E_g: 10Dq
    # 3T_{1g}(F): 15Dq + 2C
    # 3T_{1g}(P): 20Dq + C
    # 1E_g: 10Dq + 2C
    # 1T_{2g}: 15Dq
    # 1T_{1g}: 20Dq
    
    # Compute E/B for each term
    E_5Eg = (10 * Dq) / B
    E_3T1gF = (15 * Dq + 2 * C) / B
    E_3T1gP = (20 * Dq + C) / B
    E_1Eg = (10 * Dq + 2 * C) / B
    E_1T2g = (15 * Dq) / B
    E_1T1g = (20 * Dq) / B
    
    # List all terms with their E/B
    terms = [
        ("5E_g", E_5Eg),
        ("3T_{1g}(F)", E_3T1gF),
        ("3T_{1g}(P)", E_3T1gP),
        ("1E_g", E_1Eg),
        ("1T_{2g}", E_1T2g),
        ("1T_{1g}", E_1T1g)
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