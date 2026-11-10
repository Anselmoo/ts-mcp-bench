import numpy as np
from scipy.optimize import fsolve

def v2_v3(B, Dq):
    matrix = np.array([[15*Dq - 15*B, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B]])
    eigvals = np.linalg.eigvalsh(matrix)
    return eigvals[0] + 15*B, eigvals[1] + 15*B

Dq = 1750
def objective(B):
    v2, v3 = v2_v3(B[0], Dq)
    return v2 - 23860

B_sol = fsolve(objective, 600)[0]
v2, v3 = v2_v3(B_sol, Dq)
print(f"B: {B_sol:.2f}")
print(f"v2: {v2:.2f}, v3: {v3:.2f}")
