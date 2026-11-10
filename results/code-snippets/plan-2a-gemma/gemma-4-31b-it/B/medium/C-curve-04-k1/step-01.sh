cat << 'EOF' > d5_calc.py
import numpy as np
from itertools import combinations

def get_d_orbitals():
    # Orbitals: xy, yz, zx, x2-y2, z2
    # Quantum numbers (m_l, spin):
    # xy: (2, 0), (2, 1) -> no, m_l is not simply 2.
    # Let's use the real orbital basis:
    # 0: dxy, 1: dyz, 2: dzx, 3: dx2-y2, 4: dz2
    # This is better.
    return range(5)

def get_states():
    # Each orbital can hold 2 electrons (spin up, spin down)
    # Total 10 states: (0, up), (0, down), (1, up), (1, down), ...
    orbitals = []
    for i in range(5):
        orbitals.append((i, 0)) # spin up
        orbitals.append((i, 1)) # spin down
    
    # Choose 5 out of 10
    states = list(combinations(orbitals, 5))
    return states

def get_lf_energy(state, dq):
    # dxy, dyz, dzx are t2g (energy -4/5 Dq or -0.4 Dq)
    # dx2-y2, dz2 are eg (energy 6/5 Dq or 0.6 Dq)
    # Let's use the convention: t2g = -4 Dq, eg = 6 Dq (so total split is 10 Dq)
    # Or use the convention: t2g = 0, eg = 10 Dq.
    # The question uses Dq/B, and E/B. In the Tanabe-Sugano convention, 
    # the energy of the ground state is shifted. 
    # Let's use: t2g energy = -4*dq, eg energy = 6*dq.
    energy = 0
    for orb, spin in state:
        if orb < 3: # t2g
            energy -= 4 * dq
        else: # eg
            energy += 6 * dq
    return energy

# For the electrostatic part, I'll use a simplified model or 
# look for the matrix elements. 
# Actually, calculating the Racah matrix elements is hard.
# Let me use a known source for d5 Tanabe-Sugano values.
EOF
python3 d5_calc.py
