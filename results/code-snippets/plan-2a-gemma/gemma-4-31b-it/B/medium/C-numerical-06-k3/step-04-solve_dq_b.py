import numpy as np
from scipy.optimize import minimize
import itertools

def get_v(vars):
    Dq, B = vars
    term = np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    e_a2g = 0
    e_t2g = 10 * Dq
    e_t1g_f = 0.5 * (15*B + 10*Dq - term)
    e_t1g_p = 0.5 * (15*B + 10*Dq + term)
    
    # d7 ground state is T1g_F.
    # Transitions are to T2g, A2g, T1g_P.
    v = [
        e_t2g - e_t1g_f,
        e_a2g - e_t1g_f,
        e_t1g_p - e_t1g_f
    ]
    # Wait, A2g - T1g_F = 0 - e_t1g_f, which is negative.
    # This means e_t1g_f must be negative.
    # Let's use the barycenter energies:
    # e_a2g = -12*Dq
    # e_t2g = -4*Dq
    # e_t1g_f = 0.5 * (-12*Dq + 15*B - term)
    # e_t1g_p = 0.5 * (-12*Dq + 15*B + term)
    # Now for d7:
    # ground = e_t1g_f
    # v1 = e_t2g - e_t1g_f
    # v2 = e_a2g - e_t1g_f
    # v3 = e_t1g_p - e_t1g_f
    
    # Let's use these:
    e_a2g_d7 = -12 * Dq
    e_t2g_d7 = -4 * Dq
    e_t1g_f_d7 = 0.5 * (-12*Dq + 15*B - term)
    e_t1g_p_d7 = 0.5 * (-12*Dq + 15*B + term)
    
    # Check which one is the lowest
    all_e = [e_a2g_d7, e_t2g_d7, e_t1g_f_d7, e_t1g_p_d7]
    ground = min(all_e)
    diffs = sorted([e - ground for e in all_e if e != ground])
    return diffs

def objective(vars):
    diffs = get_v(vars)
    targets = [9180, 19550, 20320]
    return sum((d - t)**2 for d, t in zip(diffs, targets))

res = minimize(objective, [1000, 600], bounds=[(0, 5000), (0, 5000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Bands: {get_v(res.x)}")
