cat << 'EOF' > solution.py
import numpy as np
from scipy.linalg import eigh
from itertools import combinations

def get_cg(l1, m1, l2, m2, l3, m3):
    # This is a simple CG coefficient for l=2 cases
    # We can use a precomputed table or a simple function.
    # For the cases we need (l=2, 0, 2, 4), we can implement the formula.
    import math
    if abs(m1 + m2 - m3) > 1e-9:
        return 0.0
    
    # CG coefficients for l=2, 2, 0/2/4
    # Since we only need specific ones, let's use a small library or implement them.
    # However, it's easier to use a hardcoded table for l=2.
    return 0.0 # placeholder

# Since implementing CG coefficients is tedious, let's use the known 
# matrix elements for the Coulomb interaction in the m_l basis.
# For d-orbitals (l=2), m = -2, -1, 0, 1, 2.
# G[m1, m2, m3, m4] = <m1, m2 | 1/r12 | m3, m4>
# In terms of F0, F2, F4:
# G = F0 * a0 + F2 * a2 + F4 * a4

def get_matrix_elements(B, C):
    F0 = 0 # Shift
    F2 = 3 * (B + C)
    F4 = 7 * (C - B)
    
    # Precompute G[m1][m2][m3][m4]
    # Using the formula G = sum_k F_k / (2k+1) * sum_q <2 m1 2 q | 2 m3> <2 m2 -q | 2 m4>
    # I will use the precomputed values for d-orbitals.
    # Or just implement a simple CG function.
    return F0, F2, F4

# Let's use a simplified version for the T-S diagram.
# For d6 octahedral, the ground state is 5T2g (weak) and 1A1g (strong).
# The levels are well-known. Let's use a known implementation.
EOF
