import numpy as np
from scipy.optimize import fsolve

def energies(Dq, B):
    # Ensure Dq and B are scalars
    Dq = float(Dq)
    B = float(B)
    
    # Energies of the F-term states (relative to barycenter)
    E_T2g = -4 * Dq
    E_A2g = 6 * Dq
    
    # T1g(F) and T1g(P) mix
    mat = np.array([[-6*Dq, 6*B], [6*B, 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    E_T1g_F = eigvals[0]
    E_T1g_P = eigvals[1]
    
    return E_T1g_F, E_T2g, E_A2g, E_T1g_P

def find_B(B):
    Dq = 979
    E_T1g_F, E_T2g, E_A2g, E_T1g_P = energies(Dq, B)
    return (E_T2g - E_T1g_F) - 8620

B_sol = fsolve(find_B, 600)[0]
Dq = 979
E_T1g_F, E_T2g, E_A2g, E_T1g_P = energies(Dq, B_sol)
print(f"Dq: {Dq}, B: {B_sol}")
print(f"nu1: {E_T2g - E_T1g_F}, nu2: {E_A2g - E_T1g_F}, nu3: {E_T1g_P - E_T1g_F}")

