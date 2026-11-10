cat << 'EOF' > solver.py
import numpy as np
from itertools import combinations

def get_d_orbitals():
    # Orbitals: 0: dxy, 1: dxz, 2: dyz, 3: dxz2, 4: dx2-y2
    # t2g: 0, 1, 2; eg: 3, 4
    return np.array([0, 0, 0, 1, 1]) # 0 for t2g, 1 for eg

def calculate_energies(dq_over_b, c_over_b):
    # B is normalized to 1.
    B = 1.0
    C = c_over_b
    Dq = dq_over_b * B
    
    # Total states: 10C5 = 252
    orbitals = list(range(10)) # 0-4 spin up, 5-9 spin down
    states = list(combinations(orbitals, 5))
    n_states = len(states)
    
    H = np.zeros((n_states, n_states))
    
    # Ligand field energy
    # eg: 3,4, 8,9; t2g: 0,1,2, 5,6,7
    eg_orbitals = {3, 4, 8, 9}
    t2g_orbitals = {0, 1, 2, 5, 6, 7}
    
    # Electron repulsion matrix elements
    # For d-electrons, repulsion energy can be expressed as a sum of J integrals.
    # However, it's easier to use a simplified model or a precomputed matrix.
    # Given the constraints, I will use a basic model for the Racah parameters.
    # For d5, the repulsion is complex. Let's use the formula for the energies of the free-ion terms.
    
    # Actually, it's better to use the known TS energy values or a small-basis approximation.
    # But we need the lowest 6 levels.
    # Let's use a simplified repulsion:
    # Energy = sum_{i<j} (B * delta(l_i, l_j) + ...)
    # This is not quite right.
    
    # Let's use the energies from a TS table for d5.
    # For d5:
    # Ground state: 6A1g (E=0)
    # 4T1g(G), 4T2g(G), 4Eg(G), 4A1g(G) are the split parts of 4G.
    # 4G energy relative to 6S is 10B + 5C.
    # 4P energy relative to 6S is 15B + 10C? No.
    
    # Let's try to find a reliable way to calculate these.
    pass

EOF
