import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    C = 4.5 * B
    # Low-spin d6 octahedral transitions
    # Approximate formulas for v1, v2, v3
    # v1: 1A1g -> 1T1g
    # v2: 1A1g -> 1T2g
    # v3: 1A1g -> 1A2g
    delta = (B * (C - 4 * B)) / (10 * Dq) if Dq != 0 else 0
    v1 = 10 * Dq - 4 * B + delta
    v2 = 10 * Dq + 8 * B + delta
    v3 = 10 * Dq + 16 * B + delta
    
    observed = np.array([13960, 22740, 29700])
    calculated = np.array([v1, v2, v3])
    return np.sum((observed - calculated)**2)

res = minimize(objective, [1500, 800], bounds=[(500, 3000), (400, 1200)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
