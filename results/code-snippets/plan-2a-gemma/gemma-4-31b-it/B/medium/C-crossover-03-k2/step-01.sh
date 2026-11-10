cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def energy_hs(Dq, B, C):
    # Ground state is 5T2g. 
    # Relative to 5D barycenter:
    return -4 * Dq

def energy_ls(Dq, B, C):
    # Ground state is 1A1g.
    # Orbital energy: 6 * (-4 Dq) = -24 Dq
    # Repulsion energy: 
    # The energy of the 1A1g state relative to 5D is 15B + 10C.
    # This is a known formula for d6 octahedral complexes.
    return -24 * Dq + 15 * B + 10 * C

def transition_point(Dq, B, C):
    return energy_ls(Dq, B, C) - energy_hs(Dq, B, C)

B = 803
C = 3078
Dq_sol = fsolve(transition_point, 1000, args=(B, C))
print(f"Dq = {Dq_sol[0]}")
EOF
python3 solution.py
