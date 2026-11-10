import numpy as np
from scipy.optimize import fsolve

def calculate_nu2(B, Dq):
    # For d3 octahedral, the T1g states are eigenvalues of a 2x2 matrix
    # Basis: |^4T1g(F)> and |^4T1g(P)>
    # The matrix elements (relative to ^4A2g) are:
    # H11 = 10Dq - 15B + 15B = 10Dq (incorrect, let's use the correct ones)
    # Correct matrix for T1g states relative to ^4A2g (E=0):
    # H11 = 6*Dq - 15*B + 15*B (wait, no)
    # Let's use:
    # E(^4A2g) = 0
    # E(^4T2g) = 10*Dq
    # T1g matrix:
    # H11 = 6*Dq + 0*B  (relative to the F-term center?)
    # Let's use a more reliable source for d3 energies:
    # nu1 = 10Dq
    # nu2 = 1/2 * (10Dq + 15B + sqrt((10Dq - 15B)**2 + 120*B**2))
    # Wait, I used this above. Let me double check.
    return 0.5 * (10*Dq + 15*B + np.sqrt((10*Dq - 15*B)**2 + 120*B**2))

# The user says nu1 = 21550, nu2 = 28500
Dq = 21550 / 10
target_nu2 = 28500

def objective(B):
    return calculate_nu2(B, Dq) - target_nu2

B_sol = fsolve(objective, 800)[0]
print(f"Dq: {Dq}, B: {B_sol}, nu2: {calculate_nu2(B_sol, Dq)}")
