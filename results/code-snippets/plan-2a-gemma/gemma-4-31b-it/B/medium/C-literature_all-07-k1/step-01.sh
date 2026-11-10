cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(Dq, B, C):
    # Simplified Hamiltonian for d5 high spin quartet states
    # We focus on the G term splitting: 4T1g, 4T2g, 4Eg
    # In a real calculation, 4T1g mixes with 4T1g(P)
    
    # Energy of 4Eg (G)
    # For d5, 4Eg does not mix. Its energy relative to 6A1g:
    # E(6A1g) = 0
    # E(4Eg) = 10*B + (some C term)
    # Let's use the free ion energies.
    # E(6S) = 0
    # E(4G) = 10*B - 0.5*C (Wait, this is not standard)
    # Let's use a better source for d5 energy levels.
    # E(4Eg) = 10*B - (C/2) is for some other system.
    
    # Let's use a known approximation:
    # nu1 = -10*Dq + 10*B + 0.25*C
    # nu2 = 10*B + 0.25*C
    # nu3 = 10*B + 0.25*C + (some small Dq term)
    
    # This is not working. Let's use the T-S ratios I found.
    # nu1/B = 21, nu2/B = 23.5, nu3/B = 25 for Dq/B = 0.9
    pass

EOF
python3 solver.py
