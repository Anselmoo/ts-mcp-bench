import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    Delta = 10 * Dq
    v_obs = [9180, 19550, 20320]
    
    term = (15*B - Delta)**2 + 24*B*Delta
    if term < 0: return 1e12
    sqrt_term = np.sqrt(term)
    e_t1g_f = 0.5 * (15*B - Delta - sqrt_term)
    e_t1g_p = 0.5 * (15*B - Delta + sqrt_term)
    e_t2g = 0.5 * Delta
    e_a2g = 1.5 * Delta + 6*B
    
    # Try different assignments of v_obs to [v1, v2, v3]
    # Assignment 1: v1=T2g, v2=A2g, v3=T1gP
    v_calc1 = [e_t2g - e_t1g_f, e_a2g - e_t1g_f, e_t1g_p - e_t1g_f]
    # Assignment 2: v1=T2g, v2=T1gP, v3=A2g
    v_calc2 = [e_t2g - e_t1g_f, e_t1g_p - e_t1g_f, e_a2g - e_t1g_f]
    
    err1 = sum((a - b)**2 for a, b in zip(v_calc1, v_obs))
    err2 = sum((a - b)**2 for a, b in zip(v_calc2, v_obs))
    
    return min(err1, err2)

res = minimize(objective, [1000, 800], method='Nelder-Mead')
print(res.x)
