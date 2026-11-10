import numpy as np
from scipy.optimize import least_squares

def calculate_energies(params):
    Dq, B = params
    Delta = 10 * Dq
    
    # Matrices for the triplet states in d2 Oh
    # T2g state:
    E_T2g = Delta - 6 * B
    
    # A2g state:
    E_A2g = 3 * Delta - 15 * B
    
    # T1g states: mix of T1g(F) and T1g(P)
    # Matrix: [[-0.4*Delta - 6*B, 6*B], [6*B, 15*B - 0.4*Delta - 6*B]]
    # Wait, using a more standard form:
    # E_T1g_F = -0.4 * Delta - 6 * B
    # E_T1g_P = 15 * B - 0.4 * Delta - 6 * B
    # Mixing = 6 * B
    
    h_t1g = np.array([[-0.4 * Delta - 6 * B, 6 * B],
                     [6 * B, 15 * B - 0.4 * Delta - 6 * B]])
    e_t1g = np.linalg.eigvalsh(h_t1g)
    E_T1g_low = e_t1g[0]
    E_T1g_high = e_t1g[1]
    
    # Transition energies
    v1 = E_T2g - E_T1g_low
    v2 = E_T1g_high - E_T1g_low
    v3 = E_A2g - E_T1g_low
    
    return np.array([v1, v2, v3])

def residuals(params):
    v_obs = np.array([20700, 30570, 42990])
    v_calc = calculate_energies(params)
    return v_calc - v_obs

# Initial guess for Dq and B
# Using approximations: v3 - v1 approx 20B -> 22290/20 = 1114.5
# v1 approx Delta - 4B -> 20700 + 4458 = 25158 -> Dq = 2515.8
initial_guess = [2500, 1100]
res = least_squares(residuals, initial_guess)

Dq_sol, B_sol = res.x
print(f"Dq: {Dq_sol:.2f}")
print(f"B: {B_sol:.2f}")
print(f"Energies: {calculate_energies(res.x)}")
