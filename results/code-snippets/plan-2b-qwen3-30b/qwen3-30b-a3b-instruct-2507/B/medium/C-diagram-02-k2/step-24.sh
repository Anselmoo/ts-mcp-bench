python3 -c "import numpy as np; import matplotlib.pyplot as plt; from scipy.special import comb; from scipy.optimize import brentq; from scipy.integrate import quad; from itertools import combinations; from math import factorial; from functools import lru_cache; from collections import defaultdict; from typing import List, Tuple, Dict, Any; import warnings; warnings.filterwarnings('ignore');

# Define parameters
B = 814  # cm^-1
C = 3902  # cm^-1

# Dq/B values to compute
Dq_over_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# Free-ion terms for d^4
# Ground term: ⁵D
# Excited terms: ³H, ³G, ³F, ³P, ¹G, ¹D, ¹F

# Energy levels in cm^-1 for d^4
# ⁵D: 0
# ³H: 3627
# ³G: 4153
# ³F: 4940
# ³P: 5944
# ¹G: 8225
# ¹D: 9200
# ¹F: 11570

# Convert to B units
E_5D = 0
E_3H = 3627 / B
E_3G = 4153 / B
E_3F = 4940 / B
E_3P = 5944 / B
E_1G = 8225 / B
E_1D = 9200 / B
E_1F = 11570 / B

# For d^4, the ground state is ⁵T₂g
# The energy of ⁵T₂g is: E = 0 (by convention)
# The energy of ⁵Eg is: E = 10 * Dq/B
# The energy of ³T₁g is: E = 10 * Dq/B + 2*B
# The energy of ³T₂g is: E = 10 * Dq/B + 2*B
# The energy of ³A₂g is: E = 10 * Dq/B + 2*B
# The energy of ³T₁g (from ³H) is: E = 10 * Dq/B + 2*B + 3627/B
# The energy of ³T₂g (from ³H) is: E = 10 * Dq/B + 2*B + 3627/B
# The energy of ³A₁g (from ³H) is: E = 10 * Dq/B + 2*B + 3627/B
# The energy of ³T₁g (from ³G) is: E = 10 * Dq/B + 2*B + 4153/B
# The energy of ³T₂g (from ³G) is: E = 10 * Dq/B + 2*B + 4153/B
# The energy of ³A₁g (from ³G) is: E = 10 * Dq/B + 2*B + 4153/B
# The energy of ³T₁g (from ³F) is: E = 10 * Dq/B + 2*B + 4940/B
# The energy of ³T₂g (from ³F) is: E = 10 * Dq/B + 2*B + 4940/B
# The energy of ³A₁g (from ³F) is: E = 10 * Dq/B + 2*B + 4940/B
# The energy of ³T₁g (from ³P) is: E = 10 * Dq/B + 2*B + 5944/B
# The energy of ³T₂g (from ³P) is: E = 10 * Dq/B + 2*B + 5944/B
# The energy of ³A₁g (from ³P) is: E = 10 * Dq/B + 2*B + 5944/B
# The energy of ³T₁g (from ¹G) is: E = 10 * Dq/B + 2*B + 8225/B
# The energy of ³T₂g (from ¹G) is: E = 10 * Dq/B + 2*B + 8225/B
# The energy of ³A₁g (from ¹G) is: E = 10 * Dq/B + 2*B + 8225/B
# The energy of ³T₁g (from ¹D) is: E = 10 * Dq/B + 2*B + 9200/B
# The energy of ³T₂g (from ¹D) is: E = 10 * Dq/B + 2*B + 9200/B
# The energy of ³A₁g (from ¹D) is: E = 10 * Dq/B + 2*B + 9200/B
# The energy of ³T₁g (from ¹F) is: E = 10 * Dq/B + 2*B + 11570/B
# The energy of ³T₂g (from ¹F) is: E = 10 * Dq/B + 2*B + 11570/B
# The energy of ³A₁g (from ¹F) is: E = 10 * Dq/B + 2*B + 11570/B

# Create a dictionary to store the energy levels for each Dq/B value
energy_levels = {}

for Dq_over_B in Dq_over_B_values:
    levels = []
    # ⁵T₂g (ground state)
    levels.append(('⁵T₂g', 0.0))
    # ⁵Eg
    levels.append(('⁵Eg', 10 * Dq_over_B))
    # ³T₁g (from ³H)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_3H))
    # ³T₂g (from ³H)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_3H))
    # ³A₂g (from ³H)
    levels.append(('³A₂g', 10 * Dq_over_B + 2 + E_3H))
    # ³T₁g (from ³G)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_3G))
    # ³T₂g (from ³G)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_3G))
    # ³A₁g (from ³G)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_3G))
    # ³T₁g (from ³F)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_3F))
    # ³T₂g (from ³F)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_3F))
    # ³A₁g (from ³F)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_3F))
    # ³T₁g (from ³P)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_3P))
    # ³T₂g (from ³P)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_3P))
    # ³A₁g (from ³P)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_3P))
    # ³T₁g (from ¹G)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_1G))
    # ³T₂g (from ¹G)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_1G))
    # ³A₁g (from ¹G)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_1G))
    # ³T₁g (from ¹D)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_1D))
    # ³T₂g (from ¹D)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_1D))
    # ³A₁g (from ¹D)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_1D))
    # ³T₁g (from ¹F)
    levels.append(('³T₁g', 10 * Dq_over_B + 2 + E_1F))
    # ³T₂g (from ¹F)
    levels.append(('³T₂g', 10 * Dq_over_B + 2 + E_1F))
    # ³A₁g (from ¹F)
    levels.append(('³A₁g', 10 * Dq_over_B + 2 + E_1F))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    # Keep only the lowest 6 levels
    levels = levels[:6]
    
    # Store in dictionary
    energy_levels[Dq_over_B] = levels

# Now create the Tanabe-Sugano diagram
plt.figure(figsize=(10, 8))

# Plot each energy level
for Dq_over_B in Dq_over_B_values:
    levels = energy_levels[Dq_over_B]
    energies = [level[1] for level in levels]
    terms = [level[0] for level in levels]
    
    # Plot the energy levels
    plt.plot([Dq_over_B] * len(energies), energies, 'o', color='blue')
    
    # Add labels
    for i, (term, energy) in enumerate(zip(terms, energies)):
        plt.text(Dq_over_B + 0.05, energy, term, fontsize=8, va='center')

# Set axis labels
plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d^4 Ion (B = 814 cm⁻¹, C = 3902 cm⁻¹)')

# Set x-axis limits
plt.xlim(-0.1, 4.1)

# Add horizontal line at E/B = 0
plt.axhline(y=0, color='k', linestyle='-', alpha=0.5)

# Save the plot
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')

# Show the plot
plt.show()

# Return the results
results = []
for Dq_over_B in Dq_over_B_values:
    levels = energy_levels[Dq_over_B]
    results.append({
        'dq_over_b': Dq_over_B,
        'levels': [
            {'term': level[0], 'e_over_b': level[1]} for level in levels
        ]
    })

# Print results
for result in results:
    print(f"Dq/B = {result['dq_over_b']}")
    for level in result['levels']:
        print(f"  {level['term']}: {level['e_over_b']:.3f}")

# Return the results as JSON
import json
print(json.dumps(results))"