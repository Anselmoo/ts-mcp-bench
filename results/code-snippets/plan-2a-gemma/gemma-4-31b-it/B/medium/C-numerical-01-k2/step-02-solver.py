import numpy as np
from scipy.optimize import least_squares

def calculate_energies(params):
    Dq, B = params
    Delta = 10 * Dq
    
    E_T2g = 0.6 * Delta
    E_A2g = 2.0 * Delta
    
    h_t1g = np.array([[-0.4 * Delta, 6 * B],
                     [6 * B, 15 * B - 0.4 * Delta]])
    e_t1g = np.linalg.eigvalsh(h_t1g)
    E_T1g_low = e_t1g[0]
    E_T1g_high = e_t1g[1]
    
    v1 = E_T2g - E_T1g_low
    v2 = E_T1g_high - E_T1g_low
    v3 = E_A2g - E_T1g_low
    
    return np.array([v1, v2, v3])

def residuals(params):
    v_obs = np.array([20700, 30570, 42990])
    v_calc = calculate_energies(params)
    return v_calc - v_obs

initial_guess = [2000, 1000]
res = least_squares(residuals, initial_guess)

Dq_sol, B_sol = res.x
print(f"Dq: {Dq_sol:.2f}")
print(f"B: {B_sol:.2f}")
print(f"Energies: {calculate_energies(res.x)}")
print(f"Residuals: {residuals(res.x)}")
