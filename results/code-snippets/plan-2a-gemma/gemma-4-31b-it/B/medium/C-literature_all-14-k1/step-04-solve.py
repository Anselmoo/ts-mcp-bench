import numpy as np
from scipy.optimize import differential_evolution

def get_quartet_energies(Dq, B):
    a = -15*B - 4*Dq
    c = 15*B + 6*Dq
    b = 4 * np.sqrt(10) * Dq
    trace = a + c
    det = a*c - b**2
    delta = np.sqrt(max(0, trace**2 - 4*det))
    E_lower = (trace - delta) / 2
    E_upper = (trace + delta) / 2
    E_4T2 = -15*B - 2*Dq
    return E_lower, E_upper, E_4T2

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0: return 1e12
    E_lower, E_upper, E_4T2 = get_quartet_energies(Dq, B)
    nu1 = E_4T2 - E_lower
    nu3 = E_upper - E_lower
    return (nu1 - 8100)**2 + (nu3 - 19400)**2

result = differential_evolution(objective, [(0, 2000), (0, 2000)])
Dq, B = result.x
E_lower, E_upper, E_4T2 = get_quartet_energies(Dq, B)
print(f"Dq: {Dq}, B: {B}")
print(f"nu1: {E_4T2 - E_lower}, nu3: {E_upper - E_lower}")
