cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt
from itertools import combinations, product

def get_cg(l1, m1, l2, m2, l3, m3):
    # Simple Clebsch-Gordan for l=2
    # Only needed for <2 m1 2 q | k 0>
    # Using a pre-computed table or a simple function
    # For l=2, k=0, 2, 4
    # <2 m 2 -m | 0 0> = 1 / sqrt(5)
    # <2 m 2 -m | 2 0> = sqrt( (2*m**2 - 3) / 7 ) / sqrt(5) ... no.
    # Let's use a known table.
    
    # <2 m 2 -m | 0 0> = 1/sqrt(5)
    # <2 m 2 -m | 2 0> = (3*m**2 - 3) / (sqrt(14)*sqrt(5)) ... no.
    # Let's use the formula: <l m l -m | k 0> = (-1)^{l-m} sqrt((2k+1)/(2l+1)) * (l-m)! (l+m)! / ...
    
    # Actually, let's use the matrix elements directly.
    return 0

# Instead of CG, let's use the known repulsion matrix for d-orbitals
# based on Racah B and C.
# The energies of the terms relative to ^5D are known.
# For d4:
# ^5D: 0
# ^3F: C - 5B (no)
# Let's use the formulas for d^n terms relative to the ground state.
# d4:
# ^5D: 0
# ^3P: 15B + 2C
# ^3F: 5B + 2C (maybe?)
# Let's use a simple matrix for the d^4 case in Oh symmetry.
# Since we need 6 lowest levels, we can use the known transitions.
# The lowest 6 levels for d4 are generally:
# ^5Eg, ^5T2g, ^3T1g(F), ^3T2g(F), ^3A2g(F), ^3T1g(P)
# We can estimate their energies.

def solve_d4(dq_b, b, c):
    # energies relative to ^5D ground state (which is ^5Eg for small Dq/B)
    # E(^5Eg) = 0
    # E(^5T2g) = 10 * Dq = 10 * (dq_b * B) / B = 10 * dq_b * B
    # Let's express E/B.
    # E(^5Eg)/B = 0
    # E(^5T2g)/B = 10 * dq_b
    
    # For the triplet terms from ^3F:
    # Free ion E(^3F) relative to ^5D is roughly:
    # E(^3F) = C - 5B ... no.
    # For d2, ^3F is ground. For d4, ^5D is ground.
    # The energy difference E(^3F) - E(^5D) is approx 15B - 2C? No.
    # Let's use a standard Tanabe-Sugano value for d4.
    # For C/B = 4.79:
    # At Dq/B = 0:
    # ^5D: 0
    # ^3F: ~ 10-15 B
    # ^3P: ~ 20-25 B
    # Let's use the following simplified formulas for d4:
    # ^5Eg: 0
    # ^5T2g: 10 * dq_b
    # ^3T1g(F): (E_3F/B) + 0.5 * 10 * dq_b - some mixing
    # ^3T2g(F): (E_3F/B) + 1.0 * 10 * dq_b
    # ^3A2g(F): (E_3F/B) + 1.5 * 10 * dq_b
    # ^3T1g(P): (E_3P/B) - 0.5 * 10 * dq_b
    
    # Wait, let's use a more accurate approach. 
    # I will use the energy levels of d^4 from a T-S diagram table.
    # C/B = 4.79.
    # For d4, C/B = 4.8:
    # Dq/B=0: 5D(0), 3F(13), 3P(25), 1D(20), 1G(22), 1S(30) (Approx E/B)
    # This is not very accurate.
    pass

EOF
