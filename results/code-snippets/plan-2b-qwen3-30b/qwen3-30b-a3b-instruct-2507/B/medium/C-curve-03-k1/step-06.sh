python3 -c "
# Constants
B = 784  # cm^-1
C = 3699  # cm^-1

# Dq/B values to evaluate
dq_over_b_values = [1.45, 2.45, 3.00]

# Energy expressions (in cm^-1) for d7 octahedral terms (relative to 4T1g)
# E(4T2g) = 2*Dq - 2*B
# E(4A2g) = 4*Dq - 2*B
# E(2Eg) = 3*Dq - 2*B
# E(2T2g) = 3*Dq + 2*B
# E(2T1g) = 4*Dq + 2*B

# Store results
results = []

for dq_over_b in dq_over_b_values:
    Dq = dq_over_b * B
    
    # Energies in cm^-1 relative to 4T1g
    E_4T2g = 2*Dq - 2*B
    E_4A2g = 4*Dq - 2*B
    E_2Eg = 3*Dq - 2*B
    E_2T2g = 3*Dq + 2*B
    E_2T1g = 4*Dq + 2*B
    
    # List of excited terms with their energies (in cm^-1)
    terms = [
        (\"4T2g\", E_4T2g),
        (\"4A2g\", E_4A2g),
        (\"2Eg\", E_2Eg),
        (\"2T2g\", E_2T2g),
        (\"2T1g\", E_2T1g)
    ]
    
    # Sort by energy (ascending)
    sorted_terms = sorted(terms, key=lambda x: x[1])
    
    # Take first three excited terms
    for term, energy_cm1 in sorted_terms[:3]:
        E_over_B = energy_cm1 / B
        results.append({
            "dq_over_b": dq_over_b,
            "term": term,
            "e_over_b": E_over_B
        })

# Output results
for res in results:
    print(f"{{res['dq_over_b']}}, {{res['term']}}, {{res['e_over_b']:.6f}}")
"