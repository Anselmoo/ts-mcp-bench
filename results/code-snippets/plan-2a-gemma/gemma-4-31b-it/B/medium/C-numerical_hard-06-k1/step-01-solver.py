import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    C = 4.0 * B
    
    # Ground state E(^1A1g) = -12*Dq + 15*B + 5*C
    E_gs = -12*Dq + 15*B + 5*C
    
    # State ^1T2g: E = -2*Dq + 15*B + 5*C
    nu2 = (-2*Dq + 15*B + 5*C) - E_gs
    
    # State ^1Eg: E = 8*Dq + 15*B + 10*C
    nu3 = (8*Dq + 15*B + 10*C) - E_gs
    
    # State ^1T1g: Mixing of two states
    # psi1: -2*Dq + 12*B + 5*C
    # psi2: 8*Dq + 12*B + 10*C
    # Mixing matrix: [[E1, 4*B], [4*B, E2]]
    E1 = -2*Dq + 12*B + 5*C
    E2 = 8*Dq + 12*B + 10*C
    
    # Eigenvalues of [[E1, 4*B], [4*B, E2]]
    # lambda = (E1+E2)/2 +/- sqrt(((E1-E2)/2)**2 + (4*B)**2)
    nu1 = ((E1 + E2) / 2.0 - np.sqrt(((E1 - E2) / 2.0)**2 + (4*B)**2)) - E_gs
    
    return [nu1 - 16700, nu2 - 26330, nu3 - 35020]

# We have 3 equations and 2 variables. Let's see if a solution exists.
# Since we have more equations than variables, we might need to find the best fit
# or check if the model is consistent.
# Let's try to solve using only nu1 and nu2 first.
def solve_12(vars):
    Dq, B = vars
    C = 4.0 * B
    E_gs = -12*Dq + 15*B + 5*C
    nu2 = (-2*Dq + 15*B + 5*C) - E_gs
    E1 = -2*Dq + 12*B + 5*C
    E2 = 8*Dq + 12*B + 10*C
    nu1 = ((E1 + E2) / 2.0 - np.sqrt(((E1 - E2) / 2.0)**2 + (4*B)**2)) - E_gs
    return [nu1 - 16700, nu2 - 26330]

def solve_23(vars):
    Dq, B = vars
    C = 4.0 * B
    E_gs = -12*Dq + 15*B + 5*C
    nu2 = (-2*Dq + 15*B + 5*C) - E_gs
    nu3 = (8*Dq + 15*B + 10*C) - E_gs
    return [nu2 - 26330, nu3 - 35020]

def solve_13(vars):
    Dq, B = vars
    C = 4.0 * B
    E_gs = -12*Dq + 15*B + 5*C
    E1 = -2*Dq + 12*B + 5*C
    E2 = 8*Dq + 12*B + 10*C
    nu1 = ((E1 + E2) / 2.0 - np.sqrt(((E1 - E2) / 2.0)**2 + (4*B)**2)) - E_gs
    nu3 = (8*Dq + 15*B + 10*C) - E_gs
    return [nu1 - 16700, nu3 - 35020]

print("Solving 1&2:", fsolve(solve_12, [2000, 1000]))
print("Solving 2&3:", fsolve(solve_23, [2000, 1000]))
print("Solving 1&3:", fsolve(solve_13, [2000, 1000]))
