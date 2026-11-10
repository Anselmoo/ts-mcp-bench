import numpy as np
from scipy.optimize import least_squares

def calculate_energies(p):
    Dq, B = p
    Delta_o = 10 * Dq
    E_T2g = 0.6 * Delta_o
    E_A2g = 2.0 * Delta_o
    # Mixing matrix for T1 states
    H = np.array([[-0.4 * Delta_o, 6 * B],
                  [6 * B, 15 * B]])
    eigvals = np.linalg.eigvals(H)
    E_T1_low = min(eigvals).real
    E_T1_high = max(eigvals).real
    return np.array([E_T2g - E_T1_low, E_T1_high - E_T1_low, E_A2g - E_T1_low])

def residuals(p):
    # Trying assignment: nu1=T2g, nu2=T1g(P), nu3=A2g
    return calculate_energies(p) - np.array([15730, 24030, 32750])

# Try multiple starting points
best_res = None
min_err = float('inf')
for dq in [500, 1000, 1500, 2000]:
    for b in [500, 1000, 1500]:
        res = least_squares(residuals, [dq, b])
        err = np.sum(res.fun**2)
        if err < min_err:
            min_err = err
            best_res = res

print(f"Best Dq: {best_res.x[0]}, B: {best_res.x[1]}")
print(f"Energies: {calculate_energies(best_res.x)}")
print(f"Error: {min_err}")
