import numpy as np
from itertools import combinations, product
import matplotlib.pyplot as plt

def cg_22k0(m, k):
    # <2 m 2 -m | k 0>
    if k == 0:
        return 1.0 / np.sqrt(5)
    if k == 2:
        if m == 2: return np.sqrt(2/7) * (1/np.sqrt(5)) # Not correct
        # Use the formula: <l m l -m | k 0> = (-1)^{l-m} sqrt((2k+1)/(2l+1)) * (l-m)! (l+m)! / (2l)! * ...
        pass
    return 0

# Let's use the direct matrix elements for d-orbitals from a source.
# For d-orbitals m = {2, 1, 0, -1, -2}
# J_mm = <m m | V | m m>
# K_mn = <m n | V | n m>
# In terms of F0, F2, F4:
# J_mm = F0 - F2 - F4 (for m=0)
# J_mm = F0 - F2 + F4 (for m=1,2) ... no.

# Let's use the following approximation for E/B:
# d4 ion, C/B = 4.79
# B = 814, C = 3902
# The 6 lowest levels are:
# 1. ^5Eg (Ground state for low Dq/B)
# 2. ^5T2g (E/B = 10 * Dq/B)
# 3. ^3T1g (from 3F)
# 4. ^3T2g (from 3F)
# 5. ^3A2g (from 3F)
# 6. ^3T1g (from 3P)

# For d4, C/B = 4.8:
# At Dq/B = 0:
# ^5D: 0
# ^3F: ~12 B
# ^3P: ~24 B
# ^1D: ~18 B
# ^1G: ~22 B

def get_energies(dq_b, c_b=4.79):
    # This is a simplified model for d4 Tanabe-Sugano
    # E/B values based on standard T-S diagrams for d4, C/B=4.8
    # ground state is ^5Eg
    e_5eg = 0
    e_5t2g = 10 * dq_b
    
    # ^3F term splitting
    # Free ion E(^3F)/B approx 12
    e_3f_base = 12.0 
    e_3t1g_f = e_3f_base + 5 * dq_b - 2 * np.sqrt( (dq_b*5)**2 + 1) # mixing
    e_3t2g_f = e_3f_base + 10 * dq_b
    e_3a2g_f = e_3f_base + 15 * dq_b
    
    # ^3P term splitting
    e_3p_base = 24.0
    e_3t1g_p = e_3p_base - 5 * dq_b
    
    # Return sorted energies and labels
    levels = [
        ('^5Eg', e_5eg),
        ('^5T2g', e_5t2g),
        ('^3T1g(F)', e_3t1g_f),
        ('^3T2g(F)', e_3t2g_f),
        ('^3A2g(F)', e_3a2g_f),
        ('^3T1g(P)', e_3t1g_p)
    ]
    return sorted(levels, key=lambda x: x[1])

# Wait, this is too approximate. 
# Let's use the actual Racah parameters.
# For d4, the ground state is ^5D.
# The other terms are ^3F, ^3P, ^1D, ^1G, ^1S.
# Relative to ^5D:
# E(^3F) = C - 5B? No.
# Let's use:
# E(^3F) = C - 5B is for d2. 
# For d4, the terms are the same as d2 but shifted.
# E(d4) = E(d2) + Shift.
# The shift is the difference in repulsion between d4 and d2.
