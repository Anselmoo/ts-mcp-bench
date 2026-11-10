import numpy as np

# Constants
B = 821  # cm^-1
C = 3657  # cm^-1

# Dq/B values to analyze
dq_over_b_values = [0.90, 2.15, 3.35]

# d4 terms in octahedral field: 5E_g, 3T_{2g}, 3T_{1g}, 1T_{1g}, 1T_{2g}, 1E_g
# Ground term for d4 octahedral: 3T_{2g}
# Other terms: 5E_g, 3T_{1g}, 1T_{1g}, 1T_{2g}, 1E_g

# Energy formulas in units of B
# General form: E = a*(Dq/B) + b*(B) + c*(C) + d*(B^2/C) + e*(Dq^2/B)
# But we need term-specific expressions in units of B

# We use the standard ligand field expressions for d4 in Oh
# 3T_{2g} is ground term → E = 0 (by definition)
# 5E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)^2 / (C/B)
# 3T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B)
# 1T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B) + (B^2 / C) / B  # correction term
# 1T_{2g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B) + (B^2 / C) / B  # same as 1T_{1g}?
# 1E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)^2 / (C/B)

# Actually, standard formulas:
# For d4:
# 5E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)^2 / (C/B)
# 3T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B)
# 1T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B) + (B**2 / C) / B
# 1T_{2g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)^2 / (C/B) + (B**2 / C) / B
# 1E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)^2 / (C/B)

# But wait: 1T_{1g} and 1T_{2g} are split by spin-orbit coupling, but in the absence of SO, they are degenerate.
# However, in ligand field theory, we often treat them as distinct with same energy.
# But actually, in standard treatment, the 1T_{1g} and 1T_{2g} terms are not usually included in the basic ligand field diagram for d4.
# Let's use the correct known term energies for d4 in Oh:

# Known: for d4, the three lowest terms are:
# 3T_{2g} (ground)
# 3T_{1g} (first excited)
# 5E_g (second excited)
# Then 1T_{1g}, 1T_{2g}, 1E_g

# Standard ligand field energy expressions (in units of B):
# 3T_{2g}: 0
# 3T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)**2 / (C/B)
# 5E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)**2 / (C/B)
# 1T_{1g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)**2 / (C/B) + (B**2 / C) / B
# 1T_{2g}: E/B = 12*(Dq/B) - 3*(C/B) + (Dq/B)**2 / (C/B) + (B**2 / C) / B
# 1E_g: E/B = 6*(Dq/B) - 2*(C/B) + (Dq/B)**2 / (C/B)

# But actually, the 1T_{1g} and 1T_{2g} are not part of the main ligand field splitting; they are higher in energy.
# However, for completeness, we include them.

# Let's define:
C_over_B = C / B

# Function to compute E/B for each term
def compute_energy(dq_over_b):
    E_3T2g = 0.0
    E_3T1g = 12*dq_over_b - 3*C_over_B + (dq_over_b**2) / C_over_B
    E_5Eg = 6*dq_over_b - 2*C_over_B + (dq_over_b**2) / C_over_B
    E_1T1g = E_3T1g + (B**2 / C) / B  # correction term: B^2 / C in cm^-1, divide by B to get in units of B
    E_1T2g = E_3T1g + (B**2 / C) / B
    E_1Eg = E_5Eg
    
    terms = {
        '3T_{2g}': E_3T2g,
        '3T_{1g}': E_3T1g,
        '5E_g': E_5Eg,
        '1T_{1g}': E_1T1g,
        '1T_{2g}': E_1T2g,
        '1E_g': E_1Eg
    }
    return terms

# Compute for each Dq/B
results = {}
for dq_over_b in dq_over_b_values:
    energies = compute_energy(dq_over_b)
    # Sort by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    # Take first three
    top_three = sorted_terms[:3]
    results[dq_over_b] = top_three

# Output results
for dq_over_b in dq_over_b_values:
    print(f"Dq/B = {dq_over_b}")
    for term, e_over_b in results[dq_over_b]:
        print(f"  {term}: {e_over_b}")
