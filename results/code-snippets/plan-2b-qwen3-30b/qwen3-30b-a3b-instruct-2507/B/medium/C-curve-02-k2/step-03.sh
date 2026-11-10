python3 -c "
from math import pi

# Constants
B = 722  # cm^-1
C = 3003  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [1.00, 2.20, 3.50]

# d3 terms in octahedral field: ^4A2g, ^4T2g, ^4T1g, ^2Eg, ^2T2g, ^2T1g, ^2A2g, ^2Eg, ^2T1g
# Ground term is ^4A2g
# Excited terms: ^4T2g, ^4T1g, ^2Eg, ^2T2g, ^2T1g, ^2A2g, ^2Eg, ^2T1g

# Energy expressions for d3 in octahedral field (in cm^-1)
def energy_d3(dq_over_b, term):
    dq = dq_over_b * B
    # For d3: 
    # ^4A2g: 0 (ground)
    # ^4T2g: 10*dq - 6*B + 2*C
    # ^4T1g: 10*dq + 3*B - 3*C
    # ^2Eg: 10*dq - 2*B
    # ^2T2g: 10*dq + 4*B
    # ^2T1g: 10*dq + 6*B
    # ^2A2g: 10*dq
    # ^2Eg (second): 10*dq - 2*B (same as first ^2Eg)
    # ^2T1g: 10*dq + 6*B (same as ^2T2g)

    if term == '^4T2g':
        return 10*dq - 6*B + 2*C
    elif term == '^4T1g':
        return 10*dq + 3*B - 3*C
    elif term == '^2Eg':
        return 10*dq - 2*B
    elif term == '^2T2g':
        return 10*dq + 4*B
    elif term == '^2T1g':
        return 10*dq + 6*B
    elif term == '^2A2g':
        return 10*dq
    else:
        return 0  # fallback

# List of excited terms in order of increasing energy at low Dq
# For d3, ^4T2g is lowest excited, then ^4T1g, then ^2Eg
# But at higher Dq, ^2T2g and ^2T1g may shift

# We'll compute energies for each Dq/B and sort
results = []

for dq_over_b in dq_over_b_values:
    energies = {}
    terms = ['^4T2g', '^4T1g', '^2Eg', '^2T2g', '^2T1g', '^2A2g']
    for term in terms:
        energy_cm = energy_d3(dq_over_b, term)
        energy_B = energy_cm / B
        energies[term] = energy_B

    # Sort terms by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    # Take top 3 lowest excited terms
    top3 = sorted_terms[:3]

    for term, e_over_b in top3:
        results.append({
            'dq_over_b': dq_over_b,
            'term': term,
            'e_over_b': e_over_b
        })

# Output results
for res in results:
    print(f"{res['dq_over_b']:.2f}, {res['term']}, {res['e_over_b']:.4f}")
"