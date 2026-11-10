import numpy as np
from scipy.optimize import minimize

def calculate_nu_triplets(Dq, B):
    # Matrix for 3T1g states
    mat = np.array([[-2*Dq + 3*B, 6*Dq], [6*Dq, -2*Dq + 18*B]], dtype=float)
    lambdas = np.linalg.eigvals(mat)
    E_A2g = -12 * Dq + 3 * B
    nu_T1gs = sorted(lambdas.real - E_A2g)
    return np.array([10 * Dq, nu_T1gs[0], nu_T1gs[1]])

def objective(B_arr):
    B = B_arr[0]
    Dq = 740
    nu_calc = calculate_nu_triplets(Dq, B)
    nu_obs = np.array([7400, 12660, 23840])
    return np.sum((nu_calc - nu_obs)**2)

res = minimize(objective, [1000], method='Nelder-Mead')
B_opt = res.x[0]
print(f"B: {B_opt}")
print(f"Calculated nus: {calculate_nu_triplets(740, B_opt)}")
