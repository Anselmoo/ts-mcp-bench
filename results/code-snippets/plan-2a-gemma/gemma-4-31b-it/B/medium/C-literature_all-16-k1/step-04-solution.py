import numpy as np
from scipy.optimize import fsolve

def equations(B):
    Dq = 740
    # We use the matrix to find eigenvalues for 3T1g
    # H = [[20*Dq, 6*B], [6*B, 10*Dq + 15*B]]
    # nu2, nu3 are the eigenvalues relative to 3A2g = 0?
    # Let's try:
    # E1, E2 = np.linalg.eigvals([[20*Dq, 6*B], [6*B, 10*Dq + 15*B]])
    # But let's use the 3F 3P mixing correctly.
    # For d8, Oh:
    # 3A2g: 0
    # 3T2g: 10*Dq
    # 3T1g(F): 20*Dq
    # 3T1g(P): 10*Dq + 15*B
    # Mixing V = 6*B (approx)
    
    V = 6*B
    E_F = 20*Dq
    E_P = 10*Dq + 15*B
    # Eigenvalues of [[E_F, V], [V, E_P]]
    nu2 = 0.5 * (E_F + E_P - np.sqrt((E_F - E_P)**2 + 4*V**2))
    nu3 = 0.5 * (E_F + E_P + np.sqrt((E_F - E_P)**2 + 4*V**2))
    
    return nu2 - 12660

B_sol = fsolve(equations, 600)[0]
Dq = 740
V = 6 * B_sol
E_F = 20 * Dq
E_P = 10 * Dq + 15 * B_sol
nu2 = 0.5 * (E_F + E_P - np.sqrt((E_F - E_P)**2 + 4*V**2))
nu3 = 0.5 * (E_F + E_P + np.sqrt((E_F - E_P)**2 + 4*V**2))
print(f"B: {B_sol}, nu2: {nu2}, nu3: {nu3}")
