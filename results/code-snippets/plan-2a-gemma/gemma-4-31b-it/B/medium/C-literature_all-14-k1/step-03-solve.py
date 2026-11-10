import numpy as np
from scipy.optimize import minimize

def get_quartet_energies(Dq, B):
    # Secular matrix for 4T1 states in d7 octahedral
    # E(4T1(F)) = -15*B - 4*Dq
    # E(4T1(P)) = 15*B + 6*Dq
    # Off-diagonal = 4*sqrt(10)*Dq
    
    # Shift to make 4T1(F) the reference if B=0, Dq=0? 
    # Actually, just use the matrix and find eigenvalues.
    a = -15*B - 4*Dq
    c = 15*B + 6*Dq
    b = 4 * np.sqrt(10) * Dq
    
    # Eigenvalues of [[a, b], [b, c]]
    trace = a + c
    det = a*c - b**2
    delta = np.sqrt(max(0, trace**2 - 4*det))
    E_lower = (trace - delta) / 2
    E_upper = (trace + delta) / 2
    
    # Energy of 4T2 state
    E_4T2 = -15*B - 2*Dq
    
    # Energy of 4A2 state
    E_4A2 = -15*B + 6*Dq
    
    return E_lower, E_upper, E_4T2, E_4A2

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0: return 1e12
    
    E_lower, E_upper, E_4T2, E_4A2 = get_quartet_energies(Dq, B)
    
    # Transitions from 4T1(F)
    nu1 = E_4T2 - E_lower
    nu3 = E_upper - E_lower
    
    # Targets: nu1 = 8100, nu3 = 19400
    return (nu1 - 8100)**2 + (nu3 - 19400)**2

from scipy.optimize import differential_evolution
result = differential_evolution(objective, [(0, 5000), (0, 5000)])
Dq, B = result.x
E_lower, E_upper, E_4T2, E_4A2 = get_quartet_energies(Dq, B)
print(f"Dq: {Dq}, B: {B}")
print(f"nu1: {E_4T2 - E_lower}, nu3: {E_upper - E_lower}")
print(f"nu2: {E_4A2 - E_lower}")
