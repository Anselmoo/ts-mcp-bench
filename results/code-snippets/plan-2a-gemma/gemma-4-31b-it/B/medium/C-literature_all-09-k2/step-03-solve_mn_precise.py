import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B, C = p
    X = 15*B + 10*C
    Y = 5*B + 4*C
    
    # Using the expressions:
    # v1 = 0.5 * (X - np.sqrt(X**2 - 160*Dq*Y))
    # v2 = 0.5 * (X + np.sqrt(X**2 - 160*Dq*Y)) - 5*Dq
    # v3 = 10*B + 5*C + 5*Dq
    
    # To avoid sqrt of negative numbers during fsolve:
    term = X**2 - 160*Dq*Y
    if term < 0:
        return [1e6, 1e6, 1e6]
    
    v1 = 0.5 * (X - np.sqrt(term))
    v2 = 0.5 * (X + np.sqrt(term)) - 5*Dq
    v3 = 10*B + 5*C + 5*Dq
    
    return [v1 - 19720, v2 - 23260, v3 - 24980]

# Initial guess: Dq ~ 350, B ~ 800, C ~ 3200
p0 = [350, 800, 3200]
sol = fsolve(equations, p0)
print(sol)
