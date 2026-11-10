import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    # Matrix [[-6*Dq, 6*Dq], [6*Dq, 15*B - 6*Dq]]
    # Trace = 15*B - 12*Dq
    # Det = -90*B*Dq + 36*Dq^2 - 36*Dq^2 = -90*B*Dq
    # Term = sqrt( (15*B-12*Dq)^2 + 360*B*Dq )
    term = np.sqrt((15*B - 12*Dq)**2 + 360*B*Dq)
    e_t1f = 0.5 * (15*B - 12*Dq - term)
    e_t1p = 0.5 * (15*B - 12*Dq + term)
    e_t2 = 6 * Dq
    
    nu1 = e_t2 - e_t1f
    nu2 = e_t1p - e_t1f
    return [nu1 - 17500, nu2 - 25000]

sol = fsolve(equations, [1700, 800])
print(f"Dq: {sol[0]}, B: {sol[1]}")
