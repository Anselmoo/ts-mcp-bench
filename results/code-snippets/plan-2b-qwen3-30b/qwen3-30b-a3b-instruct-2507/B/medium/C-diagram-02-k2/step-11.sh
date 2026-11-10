python3 -c "import numpy as np; import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle; from matplotlib.collections import PatchCollection; import matplotlib.patches as mpatches; from scipy.special import comb; from scipy.optimize import brentq; from scipy.integrate import quad; from itertools import combinations; from math import factorial; from functools import lru_cache; from collections import defaultdict; from typing import List, Tuple, Dict, Any; import warnings; warnings.filterwarnings('ignore');

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

# Octahedral term symbols and their degeneracies
# ⁵T₂g (3), ⁵Eg (2), ³T₁g (3), ³T₂g (3), ³A₂g (1), ³T₁g (3), ³T₂g (3), ³A₁g (1), ³T₁g (3), ³T₂g (3), ³A₂g (1), ³T₁g (3), ³T₂g (3), ³A₁g (1), ³T₁g (3), ³T₂g (3), ³A₂g (1), ³T₁g (3), ³T₂g (3), ³A₁g (1)
# But we need to calculate the energies using the Tanabe-Sugano formalism

# The energy of a term is given by:
# E = (Dq/B) * (sum of orbital contributions) + (B) * (sum of configuration interaction terms)
# But we need to use the standard Tanabe-Sugano formulas

# For d^4, the ground state is ⁵T₂g
# The energy of ⁵T₂g is: E = 0 (by convention)
# The energy of ⁵Eg is: E = 10 * Dq/B
# The energy of ³T₁g is: E = 10 * Dq/B + 2*B
# The energy of ³T₂g is: E = 10 * Dq/B + 2*B
# The energy of ³A₂g is: E = 10 * Dq/B + 2*B
# The energy of ³T₁g (from ³H) is: E = 10 * Dq/B + 2*B + 3627/B
# The energy of ³T₂g (from ³H) is: E = 10 * Dq/B + 2*B + 3627/B
# The energy of ³A₁g (from ³H) is: E = 10 * Dq/B + 2*B + 362