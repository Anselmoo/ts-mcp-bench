import numpy as np
from scipy.optimize import minimize

def objective(params):
    Delta, B = params
    if Delta <= 0 or B <= 0: return 1e10
    
    # T1g matrix for d3
    mat = np.array([[15*B - Delta, 6*B], [6*B, 15*B]])
    eigs = np.linalg.eigvalsh(mat)
    e_t1g_low = eigs[0]
    e_t1g_high = eigs[1]
    e_t2g = Delta
    e_a2g = 0
    
    v1 = e_a2g - e_t1g_low
    v2 = e_t2g - e_t1g_low
    v3 = e_t1g_high - e_t1g_low
    
    target = np.array([9180, 19550, 20320])
    current = np.array([v1, v2, v3])
    return np.sum((current - target)**2)

res = minimize(objective, [9000, 500], method='Nelder-Mead')
print(f"10Dq: {res.x[0]:.2f}, B: {res.x[1]:.2f}")
