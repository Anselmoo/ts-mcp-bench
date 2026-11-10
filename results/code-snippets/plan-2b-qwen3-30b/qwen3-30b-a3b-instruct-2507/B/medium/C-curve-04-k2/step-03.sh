python3 -c "
from scipy.constants import value as hbar
from numpy import pi, sqrt

# Constants
B = 800  # cm^-1
C = 3473  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [1.45, 2.55, 3.25]

# For d5 octahedral, the ground term is ^6S (low-spin)
# We need to compute energies of excited terms using ligand field theory
# Terms for d5: ^6S, ^4G, ^4P, ^2H, ^2G, ^2F, ^2D, ^2P, ^2S
# But only spin-allowed and spin-forbidden terms are considered

# Energy formula in units of B:
# E = Dq * (sum of m^2) + B * (sum of (L_i - L_j)^2) + C * (sum of (L_i - L_j)(L_i - L_k))
# But for d5, we use standard ligand field energy expressions

# For octahedral d5, the terms are:
# ^6S: ground term, E = 0
# ^4G: E = 10Dq - 10B + 2C
# ^4P: E = 10Dq + 10B
# ^2H: E = 10Dq + 15B + 2C
# ^2G: E = 10Dq + 15B + 2C
# ^2F: E = 10Dq + 25B
# ^2D: E = 10Dq + 20B
# ^2P: E = 10Dq + 30B
# ^2S: E = 10Dq + 30B

# However, for d5, the standard expressions are:
# ^4G: E = 10Dq - 10B + 2C
# ^4P: E = 10Dq + 10B
# ^2H: E = 10Dq + 15B + 2C
# ^2G: E = 10Dq + 15B + 2C
# ^2F: E = 10Dq + 25B
# ^2D: E = 10Dq + 20B
# ^2P: E = 10Dq + 30B
# ^2S: E = 10Dq + 30B

# But note: ^2H and ^2G are degenerate in octahedral field

# Let's compute E/B for each term at each Dq/B
results = []
for dq_over_b in dq_over_b_values:
    Dq = dq_over_b * B
    energies = {
        '6S': 0,
        '4G': 10*dq_over_b - 10 + 2*(C/B),
        '4P': 10*dq_over_b + 10,
        '2H': 10*dq_over_b + 15 + 2*(C/B),
        '2G': 10*dq_over_b + 15 + 2*(C/B),
        '2F': 10*dq_over_b + 25,
        '2D': 10*dq_over_b + 20,
        '2P': 10*dq_over_b + 30,
        '2S': 10*dq_over_b + 30
    }
    # Sort terms by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    # Take first three (lowest excited terms)
    for term, e_over_b in sorted_terms[1:4]:  # skip ground term ^6S
        results.append({
            'dq_over_b': dq_over_b,
            'term': term,
            'e_over_b': e_over_b
        })

# Output results
for r in results:
    print(f"{r['dq_over_b']:.3f}, {r['term']}, {r['e_over_b']:.3f}")
"