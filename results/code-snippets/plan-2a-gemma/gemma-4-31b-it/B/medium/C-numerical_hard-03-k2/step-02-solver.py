import numpy as np
from scipy.optimize import minimize

def objective(p):
    Dq, B = p
    C = 4.6 * B
    H22 = 10 * Dq + 4 * B + C
    H12 = 6 * B
    nu2 = np.sqrt(H22**2 + 4 * H12**2)
    E_ground = 0.5 * (H22 - nu2)
    
    v_T1g = (10 * Dq - 4 * B + C) - E_ground
    v_A2g = (10 * Dq + 2 * B - C) - E_ground
    v_T2g_exc = nu2
    
    bands = sorted([v_T1g, v_A2g, v_T2g_exc])
    target = [22640, 22930, 25080]
    return sum((b - t)**2 for b, t in zip(bands, target))

res = minimize(objective, [2200, 500], bounds=[(0, 5000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")

Dq, B = res.x
C = 4.6 * B
H22 = 10 * Dq + 4 * B + C
H12 = 6 * B
nu2 = np.sqrt(H22**2 + 4 * H12**2)
E_ground = 0.5 * (H22 - nu2)
v_T1g = (10 * Dq - 4 * B + C) - E_ground
v_A2g = (10 * Dq + 2 * B - C) - E_ground
v_T2g_exc = nu2
print(f"Bands: {sorted([v_T1g, v_A2g, v_T2g_exc])}")
