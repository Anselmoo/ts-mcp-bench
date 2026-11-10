import numpy as np
from scipy.optimize import minimize

def calculate_energies(params):
    Dq, B = params
    if Dq < 0 or B < 0:
        return 1e10
    
    # Shift due to mixing of T1g(F) and T1g(P)
    # The matrix is [[10*Dq, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B]]
    # Let's use the eigenvalues.
    H11 = 10 * Dq
    H22 = 15 * B
    H12 = 6 * np.sqrt(10) * B
    
    trace = H11 + H22
    det = H11 * H22 - H12**2
    
    discriminant = np.sqrt(trace**2 - 4*det)
    l1 = (trace - discriminant) / 2 # Ground state
    l2 = (trace + discriminant) / 2 # T1g(P) state
    
    # The other states are T2g and A2g.
    # Relative to the same barycenter:
    # T2g is 10*Dq (if we assume no mixing)
    # A2g is 25*Dq (if we assume no mixing)
    # But T2g and A2g are not mixed.
    # However, the ground state l1 is the one that's mixed.
    # So:
    nu1 = 10 * Dq - l1
    nu2 = l2 - l1
    nu3 = 25 * Dq - l1
    
    return np.array([nu1, nu2, nu3])

def objective(params):
    observed = np.array([20700, 30570, 42990])
    calculated = calculate_energies(params)
    # Sort because we don't know the order.
    calculated = np.sort(calculated)
    return np.sum((calculated - observed)**2)

best_res = minimize(objective, [1500, 800], bounds=[(0, 5000), (0, 2000)])
print(f"Best Dq: {best_res.x[0]:.2f}, Best B: {best_res.x[1]:.2f}, Error: {best_res.fun:.2f}")
