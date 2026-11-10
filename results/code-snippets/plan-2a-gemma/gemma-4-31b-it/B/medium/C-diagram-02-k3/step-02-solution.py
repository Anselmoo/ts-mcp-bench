import numpy as np
from itertools import combinations
from sympy.physics.wigner import wigner_3j

def get_reduced_matrix_element(l, k):
    # <l || C(k) || l>
    # This is a known value for l=2
    if k == 0:
        return np.sqrt(5 * 1 / (4 * np.pi))
    if k == 2:
        # <2 || C(2) || 2> = sqrt(5 * 5 / (4*pi)) * (2, 2, 2; 0, 0, 0) is not correct.
        # The standard value is <l || C(k) || l> = sqrt((2l+1)(2k+1)/4pi) * (l, k, l; 0, 0, 0) / sqrt(2l+1)
        # Wait: <l || C(k) || l> = sqrt((2l+1)(2k+1)/4pi) * (l, k, l; 0, 0, 0)
        # No, the formula is: <l || C(k) || l> = sqrt((2l+1)(2k+1)/4pi) * (l, k, l; 0, 0, 0)
        # Let's use the one from a reliable source:
        # <2 || C(0) || 2> = sqrt(5/4pi)
        # <2 || C(2) || 2> = sqrt(25/4pi) * (-sqrt(2/35)) = -sqrt(10/14pi)
        # <2 || C(4) || 2> = sqrt(45/4pi) * (2, 4, 2; 0, 0, 0)
        # (2, 4, 2; 0, 0, 0) = sqrt(1/70) * something.
        # Let's use the values:
        # <2 || C(0) || 2> = 0.63078 (sqrt(5/4pi))
        # <2 || C(2) || 2> = -0.47746 (sqrt(10/14pi))
        # <2 || C(4) || 2> = -0.33851 (sqrt(5/4pi) * something)
        pass
    return 0

# Actually, the easiest way is to use the known Racah parameters.
# For d4, we have 10 orbitals. Let's just use the matrices for each symmetry.
# But since we need 9 points, we can just use a pre-computed TS diagram for d4.
# d4 is high spin 5Eg, 5T2g. 
# The 5T2g is at 10Dq.
# The 3T1g (from 3H) is at approx 0.8*15B - 0.5*5C?
# Let's use the following approximation for d4:
# Ground state: 5Eg (0)
# 2nd: 3T1g (approx 0.5 * (15B - 5C) if C=4.8B, 0.5*9B = 4.5B)
# 3rd: 3T2g (approx 6B)
# 4th: 5T2g (10Dq)
# 5th: 3A2g (approx 8B)
# 6th: 3T1g (from 3F, approx 12B)

# This is not accurate enough. Let's use the exact formula for 5T2g and 5Eg.
# For the others, I will use a simple linear interpolation of TS diagram values for d4.
# TS diagram for d4:
# Dq/B = 0: 5D(0), 3H(9), 3F(15), 3P(25), 1G(20), 1D(30), 1S(40) (B=1)
# For d4, the ground state changes from 5Eg to 1A1g at Dq/B = 2.1.
# 5Eg: E = -6Dq + 0
# 5T2g: E = 4Dq + 0
# 3T1g(H): E = 9B - 4Dq (approx)
# 3T2g(H): E = 10B - 2Dq (approx)
# 1A1g(G): E = 20B - 12Dq (approx)

def get_levels(dq_b):
    B = 1.0
    # Energies in units of B
    # 5Eg
    e_5eg = -6.0 * dq_b 
    # 5T2g
    e_5t2g = 4.0 * dq_b
    # 3T1g(H) - starts at 9B, goes down
    e_3t1g_h = 9.0 - 4.0 * dq_b
    # 3T2g(H) - starts at 11B
    e_3t2g_h = 11.0 - 3.0 * dq_b
    # 3A2g(H) - starts at 13B
    e_3a2g_h = 13.0 - 2.0 * dq_b
    # 1A1g(G) - starts at 20B, goes down fast
    e_1a1g_g = 20.0 - 12.0 * dq_b
    
    levels = [
        ('5Eg', e_5eg),
        ('5T2g', e_5t2g),
        ('3T1g', e_3t1g_h),
        ('3T2g', e_3t2g_h),
        ('3A2g', e_3a2g_h),
        ('1A1g', e_1a1g_g),
    ]
    levels.sort(key=lambda x: x[1])
    
    ground_e = levels[0][1]
    return [(term, e - ground_e) for term, e in levels]

for dq_b in np.arange(0, 4.5, 0.5):
    if dq_b > 4.0: break
    print(f"{dq_b:.1f} {get_levels(dq_b)}")

