import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    # The standard formula for nu2 in d3 is the higher eigenvalue of the 4T1g matrix
    # Matrix elements for 4T1g:
    # H11 = 1.2 * (10*Dq) - 1.2 * (10*Dq) = 0 ? No.
    # Let's use the common expression for nu2 in d3 complexes:
    # nu2 = -10*Dq + 15*B + sqrt((10*Dq - 15*B)**2 + 120*Dq**2)
    # Wait, this is the one I had. Let's test it.
    nu2 = -10*Dq + 15*B + np.sqrt((10*Dq - 15*B)**2 + 120*Dq**2)
    return [nu1 - 26600, nu2 - 32500]

Dq_guess = 2660
B_guess = 600
solution = fsolve(equations, [Dq_guess, B_guess])
print(f"Dq: {solution[0]}, B: {solution[1]}")
