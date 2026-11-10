cat > d3_ligand_field.py << 'EOF'
# d3 ligand-field analysis: octahedral symmetry
# Using Racah parameters: B = 722 cm⁻¹, C = 3003 cm⁻¹
# Dq/B values: 1.00, 2.20, 3.50
# Compute energy levels in units of B

from numpy import array, zeros, dot

# Racah parameters (in cm⁻¹)
B = 722
C = 3003

# Dq/B values to compute
Dq_over_B_values = [1.00, 2.20, 3.50]

# Ground term for d3: ^4F (in octahedral field, splits into ^4A2g, ^4T2g, ^4T1g)
# Excited terms: ^4P, ^2H, ^2G, ^2D, ^2F, etc.
# We are interested in the three lowest excited terms (spin-allowed or spin-forbidden)

# Define the term symbols and their degeneracies
# We'll use the standard ligand-field energy formulas for d3
# For d3, the terms are:
#   ^4F → splits into ^4A2g, ^4T2g, ^4T1g
#   ^4P → ^4T1g (spin-allowed)
#   ^2H → ^2T1g, ^2T2g
#   ^2G → ^2T1g, ^2T2g
#   ^2D → ^2Eg, ^2T2g
#   ^2F → ^2T1g, ^2T2g

# We'll use the energy expressions from standard ligand-field theory
# For d3, the energies (in cm⁻¹) are:
#   E(^4A2g) = 0 (ground)
#   E(^4T2g) = 10 Dq
#   E(^4T1g) = 10 Dq + 10 B
#   E(^4T1g from ^4P) = 10 Dq + 15 B - 3 C
#   E(^2T1g) from ^2H = 10 Dq + 15 B - 3 C
#   E(^2T1g) from ^2G = 10 Dq + 15 B - 3 C
#   E(^2T1g) from ^2D = 10 Dq + 15 B - 3 C
#   E(^2T1g) from ^2F = 10 Dq + 15 B - 3 C
#   E(^2T2g) from ^2H = 10 Dq + 15 B - 3 C + 2 C
#   E(^2T2g) from ^2G = 10 Dq + 15 B - 3 C + 2 C
#   E(^2T2g) from ^2D = 10 Dq + 15 B - 3 C + 2 C
#   E(^2T2g) from ^2F = 10 Dq + 15 B - 3 C + 2 C

# Actually, standard formula for d3:
# The ^4P term splits into ^4T1g (spin-allowed)
# Energy of ^4T1g from ^4P: E = 10 Dq + 15 B - 3 C
# The ^2H, ^2G, ^2D, ^2F terms all split into ^2T1g and ^2T2g
# For ^2T1g: E = 10 Dq + 15 B - 3 C
# For ^2T2g: E = 10 Dq + 15 B - 3 C + 2 C = 10 Dq + 15 B - C

# But note: the ^2T2g from ^2H, ^2G, ^2D, ^2F all have same energy?
# Actually, they are degenerate in octahedral field

# So the excited terms:
#   ^4T1g (from ^4P): E = 10 Dq + 15 B - 3 C
#   ^2T1g (from ^2H, ^2G, ^2D, ^2F): E = 10 Dq + 15 B - 3 C
#   ^2T2g (from ^2H, ^2G, ^2D, ^2F): E = 10 Dq + 15 B - C

# Also, ^2H, ^2G, ^2D, ^2F are all spin-forbidden, but we include them as per question

# Now compute energies in units of B
# We need to compute E/B = (energy in cm⁻¹) / B

# Initialize list to store results
results = []

for Dq_over_B in Dq_over_B_values:
    Dq = Dq_over_B * B
    
    # Compute energies in cm⁻¹
    E_4T1g_P = 10 * Dq + 15 * B - 3 * C  # from ^4P
    E_2T1g = 10 * Dq + 15 * B - 3 * C  # from ^2H, ^2G, ^2D, ^2F
    E_2T2g = 10 * Dq + 15 * B - C      # from ^2H, ^2G, ^2D, ^2F
    
    # Convert to E/B
    E_B_4T1g_P = E_4T1g_P / B
    E_B_2T1g = E_2T1g / B
    E_B_2T2g = E_2T2g / B
    
    # Collect terms in order of increasing energy
    terms = [
        {'term': '^4T1g (from ^4P)', 'e_over_b': E_B_4T1g_P},
        {'term': '^2T1g (from ^2H, ^2G, ^2D, ^2F)', 'e_over_b': E_B_2T1g},
        {'term': '^2T2g (from ^2H, ^2G, ^2D, ^2F)', 'e_over_b': E_B_2T2g}
    ]
    
    # Sort by energy
    terms.sort(key=lambda x: x['e_over_b'])
    
    # Append to results
    for term in terms:
        results.append({
            'dq_over_b': Dq_over_B,
            'term': term['term'],
            'e_over_b': term['e_over_b']
        })

# Output results
for res in results:
    print(f"{res['dq_over_b']:.2f}, {res['term']}, {res['e_over_b']:.6f}")
EOF