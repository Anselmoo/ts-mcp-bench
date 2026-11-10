cat << 'EOF' > solver_v4.py
import numpy as np
from scipy.optimize import least_squares

def get_energies(p):
    B, Dq = p
    if B <= 0 or Dq <= 0: return [1e6]*3
    E_T2g = 10*Dq - 3*B
    E_A2g = 20*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    disc = np.sqrt(trace**2 - 4*det)
    E_ground = 0.5 * (trace - disc)
    E_T1g_P = 0.5 * (trace + disc)
    return E_T2g - E_ground, E_A2g - E_ground, E_T1g_P - E_ground

def equations(p):
    B, Dq = p
    calc_nus = get_energies(p)
    target_nus = [15490, 24500, 32330]
    return [calc_nus[i] - target_nus[i] for i in range(3)]

for b0 in [400, 600, 800]:
    for dq0 in [500, 800, 1100]:
        res = least_squares(equations, [b0, dq0])
        if np.allclose(res.fun, 0, atol=100):
            print(f'B: {res.x[0]}, Dq: {res.x[1]}, nus: {get_energies(res.x)}')
EOF
python3 solver_v4.py
