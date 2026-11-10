import numpy as np
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    Delta = 10 * Dq
    if Delta < 0 or B < 0: return 1e12
    
    term1 = 15 * B - Delta
    term2 = (15 * B + Delta)**2 + 144 * B**2
    
    e_t1f = (term1 - np.sqrt(term2)) / 2
    e_t1p = (term1 + np.sqrt(term2)) / 2
    e_t2g = Delta
    e_a2g = 3 * Delta
    
    nu1 = e_t2g - e_t1f
    nu2 = e_t1p - e_t1f
    nu3 = e_a2g - e_t1f
    
    obs = np.array([15490, 24500, 32330])
    calc = np.array([nu1, nu2, nu3])
    return np.sum((obs - calc)**2)

# Use a finer grid for initial guesses
best_err = 1e15
best_vars = None
for dq in np.linspace(500, 1200, 30):
    for b in np.linspace(400, 1200, 30):
        res = minimize(objective, [dq, b], method='Nelder-Mead')
        if res.fun < best_err:
            best_err = res.fun
            best_vars = res.x

print(f"Best Dq: {best_vars[0]}, B: {best_vars[1]}, Error: {best_err}")
