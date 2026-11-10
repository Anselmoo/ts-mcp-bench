import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    C = 4.6 * B
    H22 = 10 * Dq + 4 * B + C
    H12 = 6 * B
    nu2 = np.sqrt(H22**2 + 4 * H12**2)
    E_ground = 0.5 * (H22 - nu2)
    
    # Potential transitions
    v_T1g = (10 * Dq - 4 * B + C) - E_ground
    v_A2g = (10 * Dq + 2 * B - C) - E_ground
    v_T2g_exc = nu2 - E_ground # This is actually E_exc - E_gr = nu2 - E_gr = nu2 - 0.5(H22-nu2) = 1.5*nu2 - 0.5*H22
    # Wait, E_exc = 0.5 * (H22 + nu2). So E_exc - E_gr = nu2.
    v_T2g_exc = nu2
    
    # The three observed bands
    bands = sorted([v_T1g, v_A2g, v_T2g_exc])
    target = [22640, 22930, 25080]
    return [bands[0] - target[0], bands[1] - target[1], bands[2] - target[2]]

# We only have 2 variables, but 3 equations. Let's try to find the best fit for Dq, B.
# We can't use fsolve for 3 eqs and 2 vars. Let's use a simple grid search or minimize.
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

res = minimize(objective, [2000, 500], bounds=[(0, 5000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
