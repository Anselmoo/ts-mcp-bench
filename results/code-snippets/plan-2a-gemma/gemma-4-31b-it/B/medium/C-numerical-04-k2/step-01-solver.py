import numpy as np
from scipy.optimize import fsolve

def energies(params):
    Dq, B = params
    # Energies of the F-term states (relative to barycenter)
    # T2g and A2g do not mix with other states of the same symmetry
    E_T2g = -4 * Dq
    E_A2g = 6 * Dq
    
    # T1g(F) and T1g(P) mix
    # Matrix: [[-6*Dq, 6*B], [6*B, 15*B]]
    mat = np.array([[-6*Dq, 6*B], [6*B, 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    E_T1g_F = eigvals[0]
    E_T1g_P = eigvals[1]
    
    return E_T1g_F, E_T2g, E_A2g, E_T1g_P

def equations(params):
    Dq, B = params
    E_T1g_F, E_T2g, E_A2g, E_T1g_P = energies((Dq, B))
    
    nu1 = E_T2g - E_T1g_F
    nu2 = E_A2g - E_T1g_F
    nu3 = E_T1g_P - E_T1g_F
    
    return [nu1 - 8620, nu2 - 18410, nu3 - 20250]

# We have 3 equations and 2 variables (Dq, B). 
# Let's see if they are consistent or if we need to find the best fit.
# Actually, let's just use nu1 and nu2 to find Dq and B, then check nu3.
# nu2 - nu1 = E_A2g - E_T2g = 6*Dq - (-4*Dq) = 10*Dq
# 18410 - 8620 = 9790 = 10*Dq => Dq = 979

Dq_fixed = 979
def find_B(B):
    E_T1g_F, E_T2g, E_A2g, E_T1g_P = energies((Dq_fixed, B))
    return (E_T2g - E_T1g_F) - 8620

B_sol = fsolve(find_B, 600)[0]
E_T1g_F, E_T2g, E_A2g, E_T1g_P = energies((Dq_fixed, B_sol))
print(f"Dq: {Dq_fixed}, B: {B_sol}")
print(f"nu1: {E_T2g - E_T1g_F}, nu2: {E_A2g - E_T1g_F}, nu3: {E_T1g_P - E_T1g_F}")

