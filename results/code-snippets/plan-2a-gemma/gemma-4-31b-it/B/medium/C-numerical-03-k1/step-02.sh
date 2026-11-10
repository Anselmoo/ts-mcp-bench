cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import least_squares

def get_energies(p):
    B, Dq = p
    # 3F states (unperturbed by 3P)
    # The energies of 3T1g, 3T2g, 3A2g relative to the barycenter of 3F
    # Using the standard formulas:
    # E(T2g) = 10*Dq - 3*B
    # E(A2g) = 20*Dq - 3*B
    # E(T1g,F) = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    # The interaction with 3T1g,P:
    # E(T1g,P) = 15*B - 3*B = 12*B (relative to barycenter of 3F)
    # Wait, 3P is at 15B relative to the 3F barycenter.
    # And the 3P state transforms as T1g.
    # Let's use E(T1g,P_unperturbed) = 15*B.
    # But we must subtract 3B to keep the barycenter? 
    # Actually, the 3P term energy is 15B.
    # Let's check a reliable source for the T1g,P energy.
    # Most sources say E(3P) = 15B.
    # The interaction is 6B.
    
    E_T2g = 10*Dq - 3*B
    E_A2g = 20*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B # Relative to 3F barycenter
    
    # Interaction between T1g,F and T1g,P
    # Matrix: [[E_T1g_F_un, 6*B], [6*B, E_T1g_P_un]]
    # Eigenvalues:
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    # lambda^2 - trace*lambda + det = 0
    # lambda = (trace +/- sqrt(trace^2 - 4*det)) / 2
    term = np.sqrt(trace**2 - 4*det)
    E_T1g_ground = 0.5 * (trace - term)
    E_T1g_excited = 0.5 * (trace + term)
    
    return E_T1g_ground, E_T2g, E_A2g, E_T1g_excited

def equations(p):
    B, Dq = p
    E_ground, E_T2g, E_A2g, E_T1g_P = get_energies(p)
    return [
        E_T2g - E_ground - 15490,
        E_A2g - E_ground - 24500,
        E_T1g_P - E_ground - 32330
    ]

res = least_squares(equations, [600, 900])
print(f'B: {res.x[0]}, Dq: {res.x[1]}')
print(f'Residuals: {res.fun}')
EOF
python3 solver.py
