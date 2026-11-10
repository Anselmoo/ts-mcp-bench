python3 -c "
# Constants
B = 800  # cm^-1
C = 3473  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [1.45, 2.55, 3.25]

# Compute C/B
C_over_B = C / B

# Energy expressions in units of B
# ^6S: ground term, E/B = 0
# ^4G: E/B = 10*Dq/B - 10 + 2*(C/B)
# ^4P: E/B = 10*Dq/B + 10
# ^2H: E/B = 10*Dq/B + 15 + 2*(C/B)
# ^2G: E/B = 10*Dq/B + 15 + 2*(C/B)
# ^2F: E/B = 10*Dq/B + 25
# ^2D: E/B = 10*Dq/B + 20
# ^2P: E/B = 10*Dq/B + 30
# ^2S: E/B = 10*Dq/B + 30

# Prepare results
results = []
for dq_over_b in dq_over_b_values:
    energies = {
        '6S': 0,
        '4G': 10*dq_over_b - 10 + 2*C_over_B,
        '4P': 10*dq_over_b + 10,
        '2H': 10*dq_over_b + 15 + 2*C_over_B,
        '2G': 10*dq_over_b + 15 + 2*C_over_B,
        '2F': 10*dq_over_b + 25,
        '2D': 10*dq_over_b + 20,
        '2P': 10*dq_over_b + 30,
        '2S': 10*dq_over_b + 30
    }
    # Sort terms by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    # Take first three (lowest excited terms)
    for term, e_over_b in sorted_terms[1:4]:
        results.append({
            'dq_over_b': dq_over_b,
            'term': term,
            'e_over_b': e_over_b
        })

# Output results in required format
for r in results:
    print(f"{r['dq_over_b']:.3f}, {r['term']}, {r['e_over_b']:.3f}")
"