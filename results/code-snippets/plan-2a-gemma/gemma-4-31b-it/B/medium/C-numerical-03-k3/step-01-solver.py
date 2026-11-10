import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    Delta = 10 * Dq
    
    # Matrix for T1g states
    # E(T1g, F) = -2 * Delta
    # E(T1g, P) = 15 * B
    # Mixing = 6 * B
    
    # The eigenvalues of [[-2*Delta, 6*B], [6*B, 15*B]]
    # Characteristic equation: (lambda + 2*Delta)(lambda - 15*B) - 36*B**2 = 0
    # lambda^2 + (2*Delta - 15*B)*lambda - 30*B*Delta - 36*B**2 = 0
    # lambda = [ -(2*Delta - 15*B) +/- sqrt((2*Delta - 15*B)**2 + 4*(30*B*Delta + 36*B**2)) ] / 2
    
    term1 = 2 * Delta - 15 * B
    term2 = (2 * Delta - 15 * B)**2 + 4 * (30 * B * Delta + 36 * B**2)
    
    e_t1f = (-term1 - np.sqrt(term2)) / 2
    e_t1p = (-term1 + np.sqrt(term2)) / 2
    
    # Other states (relative to T1g barycenter)
    # E(T2g) = 0
    # E(A2g) = 2 * Delta
    e_t2g = 0
    e_a2g = 2 * Delta
    
    # Transitions
    nu1 = e_t2g - e_t1f
    nu2 = e_t1p - e_t1f
    nu3 = e_a2g - e_t1f
    
    # Observed transitions
    obs_nu1 = 15490
    obs_nu2 = 24500
    obs_nu3 = 32330
    
    return [nu1 - obs_nu1, nu3 - obs_nu3] # Use nu1 and nu3 to find Dq, B

# Initial guess: Dq = 1000, B = 600
solution = fsolve(equations, [1000, 600])
print(f"Dq: {solution[0]}, B: {solution[1]}")

# Now check nu2 with these values
Dq, B = solution
Delta = 10 * Dq
term1 = 2 * Delta - 15 * B
term2 = (2 * Delta - 15 * B)**2 + 4 * (30 * B * Delta + 36 * B**2)
e_t1f = (-term1 - np.sqrt(term2)) / 2
e_t1p = (-term1 + np.sqrt(term2)) / 2
nu2 = e_t1p - e_t1f
print(f"Calculated nu2: {nu2}")
