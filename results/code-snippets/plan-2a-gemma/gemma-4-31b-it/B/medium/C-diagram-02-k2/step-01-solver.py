import numpy as np
from itertools import combinations

def get_d_orbitals():
    return ['xy', 'xz', 'yz', 'z2', 'x2y2']

def get_all_states(n_electrons=4):
    orbitals = []
    for orb in get_d_orbitals():
        orbitals.append((orb, 'up'))
        orbitals.append((orb, 'down'))
    
    states = []
    for combo in combinations(range(10), n_electrons):
        states.append(combo)
    return states

def compute_hamiltonian(dq, b, c, states):
    n = len(states)
    h = np.zeros((n, n))
    
    # LF Hamiltonian
    # t2g: xy, xz, yz (index 0, 1, 2)
    # eg: z2, x2y2 (index 3, 4)
    # energy: t2g = -0.4 * 10Dq, eg = 0.6 * 10Dq
    # However, it's simpler to use: t2g = 0, eg = 10Dq
    # Or t2g = -4Dq, eg = 6Dq
    
    # For each state, calculate LF energy
    # A state is a tuple of indices (0-9)
    # 0: xy_up, 1: xy_down, 2: xz_up, 3: xz_down, 4: yz_up, 5: yz_down, 6: z2_up, 7: z2_down, 8: x2y2_up, 9: x2y2_down
    # t2g indices: 0, 1, 2, 3, 4, 5
    # eg indices: 6, 7, 8, 9
    
    for i in range(n):
        state = states[i]
        energy = 0
        for idx in state:
            if idx >= 6:
                energy += 6 * dq # using 10Dq = 10*dq
            else:
                energy -= 4 * dq
        h[i, i] = energy
        
    return h

# To handle Coulomb interaction, we need the matrix elements.
# Instead of implementing the full Coulomb matrix, 
# I'll use the known Tanabe-Sugano levels for d4.
# For d4, the levels are:
# 5Eg, 5T2g, 3T1g, 3T2g, 3Eg, 3A2g ...
# Wait, for d4, the ground state is 5Eg.
# The first excited state is 5T2g at 10Dq.
# The next ones are triplets.
