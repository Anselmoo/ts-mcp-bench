import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    nu1 = 10 * Dq
    nu2 = 0.5 * (15*B + 30*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    nu3 = 0.5 * (15*B + 30*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    target = np.array([4070, 7030, 16400])
    calc = np.array([nu1, nu2, nu3])
    return np.sum((target - calc)**2)

res = minimize(objective, [400, 800], bounds=[(0, 2000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Calculated: {get_energies_new(res.x)}")
