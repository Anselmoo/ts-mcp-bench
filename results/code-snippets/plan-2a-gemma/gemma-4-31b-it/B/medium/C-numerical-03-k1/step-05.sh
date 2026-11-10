cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    B, Dq = p
    # Relative to barycenter of 3F
    # E(T2g) = 10Dq - 3B
    # E(A2g) = 20Dq - 3B
    # E(T1g,F) = 0.5 * (-15B + 10Dq - sqrt((15B-10Dq)^2 + 120B*10Dq))
    # E(T1g,P) = 15B
    # Interaction V = 6B
    
    E_T2g = 10*Dq - 3*B
    E_A2g = 20*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    
    # Matrix eigenvalues for the two T1g states
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    disc = np.sqrt(trace**2 - 4*det)
    E_ground = 0.5 * (trace - disc)
    E_T1g_P = 0.5 * (trace + disc)
    
    return [
        E_T2g - E_ground - 15490,
        E_T1g_P - E_ground - 32330
    ]

# We can use nu2 - nu1 = 10Dq to start: Dq = 901
res = fsolve(equations, [600, 901])
print(f'B: {res[0]}, Dq: {res[1]}')
EOF
python3 solver.py
