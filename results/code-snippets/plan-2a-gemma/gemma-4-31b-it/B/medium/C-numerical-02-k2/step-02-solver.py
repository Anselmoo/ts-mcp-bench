import numpy as np
from scipy.optimize import minimize

def get_nu(Dq, B):
    Delta = 10 * Dq
    # T1g energies
    term_sqrt = np.sqrt((2 * B + Delta)**2 + 144 * B**2)
    e_t1_f = (B - term_sqrt) / 2
    e_t1_p = (B + term_sqrt) / 2
    
    e_t2_f = -0.5 * B + 0.5 * Delta
    e_a2_f = 0.5 * B + Delta
    
    nu1 = e_t2_f - e_t1_f
    nu2 = e_a2_f - e_t1_f
    nu3 = e_t1_p - e_t1_f
    
    return nu1, nu2, nu3

def objective(params):
    Dq, B = params
    if Dq <= 0 or B <= 0: return 1e10
    
    nu1, nu2, nu3 = get_nu(Dq, B)
    target = np.array([9460, 20160, 21160])
    current = np.array([nu1, nu2, nu3])
    
    return np.sum((target - current)**2)

# Try different starting points
best_res = None
best_fun = 1e10
for d0 in [500, 1000, 1500]:
    for b0 in [500, 800, 1200]:
        res = minimize(objective, x0=[d0, b0], method='Nelder-Mead')
        if res.fun < best_fun:
            best_fun = res.fun
            best_res = res

print(best_res.x)
print(get_nu(*best_res.x))
