import numpy as np
from scipy.optimize import least_squares

def energies(Dq, B):
    v1 = 10 * Dq
    matrix = np.array([[15*Dq - 15*B, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B]])
    eigvals = np.linalg.eigvalsh(matrix)
    v2 = eigvals[0] + 15*B
    v3 = eigvals[1] + 15*B
    return v1, v2, v3

def objective(params):
    Dq, B = params
    v1, v2, v3 = energies(Dq, B)
    return [v1 - 17500, v2 - 23860, v3 - 37910]

Dq_init, B_init = 1750, 600
res = least_squares(objective, [Dq_init, B_init])
Dq, B = res.x
v1, v2, v3 = energies(Dq, B)
print(f"Dq: {Dq:.2f}, B: {B:.2f}")
print(f"v1: {v1:.2f}, v2: {v2:.2f}, v3: {v3:.2f}")
