import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    Delta_o = 10 * Dq
    # Energy of T2g relative to F barycenter
    E_T2g = 0.6 * Delta_o
    # Energy of A2g relative to F barycenter
    E_A2g = 2.0 * Delta_o
    
    # T1 states mixing matrix
    # [[E(T1g,F), 6B], [6B, E(T1g,P)]]
    # E(T1g,F) = -0.4 * Delta_o
    # E(T1g,P) = 15 * B
    H = np.array([[-0.4 * Delta_o, 6 * B],
                  [6 * B, 15 * B]])
    
    eigenvalues = np.linalg.eigvals(H)
    E_T1_low = min(eigenvalues)
    E_T1_high = max(eigenvalues)
    
    # Transitions from ground state T1_low
    nu1 = E_T2g - E_T1_low
    nu2 = E_T1_high - E_T1_low
    nu3 = E_A2g - E_T1_low
    
    return nu1, nu2, nu3

def equations(p):
    Dq, B = p
    nu1, nu2, nu3 = calculate_energies(Dq, B)
    # We have 3 equations and 2 unknowns. We can use a least squares or solve 2.
    # Given the precision, we use nu1 and nu2.
    return [nu1 - 15730, nu2 - 24030]

# Initial guess
Dq_guess = 1200
B_guess = 1000
res = fsolve(equations, [Dq_guess, B_guess])
Dq_sol, B_sol = res
nu1_sol, nu2_sol, nu3_sol = calculate_energies(Dq_sol, B_sol)

print(f"Dq: {Dq_sol}")
print(f"B: {B_sol}")
print(f"Nu1: {nu1_sol}, Nu2: {nu2_sol}, Nu3: {nu3_sol}")
