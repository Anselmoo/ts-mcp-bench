import numpy as np
from scipy.optimize import minimize

def get_energies(Dq, B):
    # Simple model for d7 high spin
    # T1 states mixing
    # H = [[-4*Dq, 4*np.sqrt(10)*Dq], [4*np.sqrt(10)*Dq, 6*Dq + 15*B]]
    # The B term in the -4Dq is often omitted or part of the barycenter.
    # Let's use the energy formula from a known source:
    # E(T1g(F)) = -4Dq - B (approx)
    # E(T2g) = -2Dq + 2B (approx)
    # E(A2g) = 6Dq - B (approx)
    # E(T1g(P)) = 6Dq + 15B - B = 6Dq + 14B (approx)
    
    # Let's try the most basic one first:
    a = -4 * Dq
    b = 4 * np.sqrt(10) * Dq
    c = 6 * Dq + 15 * B
    
    trace = a + c
    det = a * c - b**2
    delta = np.sqrt(max(0, trace**2 - 4*det))
    E1 = (trace - delta) / 2
    E3 = (trace + delta) / 2
    
    E2 = -2 * Dq
    E_A2 = 6 * Dq
    
    return np.array([E2 - E1, E_A2 - E1, E3 - E1])

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0: return 1e12
    target = np.array([8100, 19400, 21600])
    current = get_energies(Dq, B)
    return np.sum((current - target)**2)

from scipy.optimize import differential_evolution
result = differential_evolution(objective, [(0, 5000), (0, 5000)])
print(f"Dq: {result.x[0]}, B: {result.x[1]}")
print(f"Energies: {get_energies(*result.x)}")
