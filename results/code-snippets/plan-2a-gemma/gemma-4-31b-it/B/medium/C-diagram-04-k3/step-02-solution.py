import numpy as np
from scipy.linalg import eigh
from itertools import combinations

def cg_222(m1, q, m3):
    # Precomputed CG coefficients <2 m1 2 q | 2 m3>
    # Only those where m1+q = m3
    table = {
        (2, -2, 2): np.sqrt(1/10),
        (2, -1, 1): np.sqrt(1/5),
        (2, 0, 2): np.sqrt(2/5), # Wait, m1+q = m3
    }
    # Actually, let's use a more complete table or formula.
    return 0.0

# To be more accurate, I will use the following matrix for the 
# d6 octahedral problem.
# Since I can't implement the full diagonalization quickly,
# I'll use the known transitions for d6 octahedral.
# d6 octahedral: 
# Ground state: 5T2g (weak), 1A1g (strong)
# The 6 lowest levels:
# 1. 5T2g / 1A1g
# 2. 5Eg
# 3. 3T1g (from 3H)
# 4. 3T2g (from 3H)
# 5. 3E g (from 3H)
# 6. 3T1g (from 3P)

# For d6, the energy of 5Eg is 10 Dq.
# The energy of 3T1g (from 3H) is roughly 
# E = -10 Dq + (something depending on B and C).

# Let's use a simpler approximation:
# For d6, the T-S diagram has:
# 5T2g: E = 0
# 5Eg: E = 10 Dq
# 3T1g: E = 10 Dq + ... (Wait, this is not simple)

# I'll try to find the 6 lowest levels for the given B and C.
# B = 551, C = 2511.
# Dq/B = 0, 0.5, ..., 4.0.

def get_levels(dq_over_b, B, C):
    # This is a mock function. I'll replace it with a better one.
    # In a real scenario, I'd use the diagonalization.
    # For d6:
    # 5T2g: 0
    # 5Eg: 10 * Dq
    # 3T1g: ...
    # Let's use a simplified model.
    dq = dq_over_b * B
    levels = [
        ("5T2g", 0),
        ("5Eg", 10 * dq / B),
        ("3T1g", (10 * dq + 15 * B) / B), # rough
        ("3T2g", (10 * dq + 20 * B) / B), # rough
        ("3Eg", (10 * dq + 25 * B) / B),  # rough
        ("3T1g", (10 * dq + 30 * B) / B), # rough
    ]
    return levels

# Let's try to implement the diagonalization properly.
