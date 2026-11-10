import numpy as np
from scipy.optimize import minimize

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
    v_A2g = E_A2g - E_T1g_low
    v_T1gP = E_T1g_high - E_T1g_low
    
    # We test different assignments:
    # Case 1: v1, v_T1gP, v_A2g
    # Case 2: v1, v_A2g, v_T1gP
    return v1, v_A2g, v_T1gP

def objective_case2(params):
    v_obs = np.array([20700, 30570, 42990])
    v1, v_A2g, v_T1gP = calculate_energies(params)
    v_calc = np.array([v1, v_A2g, v_T1gP])
    return np.sum((v_calc - v_obs)**2)

initial_guess = [1500, 1500]
res = minimize(objective_case2, initial_guess)

Dq_sol, B_sol = res.x
print(f"Dq: {Dq_sol:.2f}")
print(f"B: {B_sol:.2f}")
v1, v_A2g, v_T1gP = calculate_energies(res.x)
print(f"Energies: {np.array([v1, v_A2g, v_T1gP])}")
print(f"Residuals: {np.array([v1, v_A2g, v_T1gP]) - np.array([20700, 30570, 42990])}")
