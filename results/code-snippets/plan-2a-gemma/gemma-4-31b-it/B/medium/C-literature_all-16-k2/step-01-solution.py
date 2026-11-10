import numpy as np
from scipy.optimize import minimize

def calculate_nu(Dq, B):
    nu1 = 10 * Dq
    # Matrix for 3T1g states
    # H = [[-2*Dq + 3*B, 6*Dq], [6*Dq, -2*Dq + 18*B]]
    # Eigenvalues:
    # lambda = 1/2 [ (-4*Dq + 21*B) +/- sqrt((-4*Dq + 21*B)^2 - 4*(-2*Dq + 3*B)*(-2*Dq + 18*B) - 4*(6*Dq)**2) ]
    # Let's use np.linalg.eigvals for clarity
    mat = np.array([[-2*Dq + 3*B, 6*Dq], [6*Dq, -2*Dq + 18*B]])
    lambdas = np.linalg.eigvals(mat)
    E_A2g = -12 * Dq + 3 * B
    nu_T1gs = sorted(lambdas - E_A2g)
    return np.array([nu1, nu_T1gs[0], nu_T1gs[1]])

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0:
        return 1e10
    nu_calc = calculate_nu(Dq, B)
    nu_obs = np.array([7400, 12660, 23840])
    return np.sum((nu_calc - nu_obs)**2)

res = minimize(objective, [740, 1000], method='Nelder-Mead')
Dq_opt, B_opt = res.x
print(f"Dq: {Dq_opt}, B: {B_opt}")
print(f"Calculated nus: {calculate_nu(Dq_opt, B_opt)}")
