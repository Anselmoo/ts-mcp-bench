import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    Delta = 10 * Dq
    # Matrix for T1 states relative to 4F barycenter
    # H11: 4T1(F), H22: 4T1(P)
    h11 = -0.6 * Delta + 6 * B
    h22 = 0.6 * Delta + 9 * B
    h12 = 4 * np.sqrt(10) * Dq
    
    mat = np.array([[h11, h12], [h12, h22]])
    evals = np.linalg.eigvalsh(mat)
    
    e_4t1_f = evals[0]
    e_4t1_p = evals[1]
    e_4t2 = -0.6 * Delta + 6 * B
    e_4a2 = 1.2 * Delta - 6 * B
    
    v1 = e_4t2 - e_4t1_f
    v2 = e_4t1_p - e_4t1_f
    v3 = e_4a2 - e_4t1_f
    
    return v1, v2, v3

def equations(p):
    Dq, B = p
    v1, v2, v3 = calculate_energies(Dq, B)
    return [v1 - 8100, v2 - 19400]

sol = fsolve(equations, [900, 900])
print(f"Dq: {sol[0]}, B: {sol[1]}")
v1, v2, v3 = calculate_energies(sol[0], sol[1])
print(f"v1: {v1}, v2: {v2}, v3: {v3}")
