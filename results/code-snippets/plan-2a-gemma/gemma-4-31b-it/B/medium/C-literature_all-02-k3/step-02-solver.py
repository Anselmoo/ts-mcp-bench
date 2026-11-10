import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    # 3T1(F) and 3T1(P) eigenvalues from matrix [[-6*Dq, 6*np.sqrt(10)*Dq], [6*np.sqrt(10)*Dq, 15*B - 6*Dq]]
    # Trace = 15*B - 12*Dq
    # Det = (-6*Dq)*(15*B - 6*Dq) - 360*Dq**2 = -90*B*Dq + 36*Dq**2 - 360*Dq**2 = -90*B*Dq - 324*Dq**2
    # E = [ (15*B - 12*Dq) +/- sqrt((15*B - 12*Dq)**2 - 4*Det) ] / 2
    
    term = np.sqrt((15*B - 12*Dq)**2 + 4*(90*B*Dq + 324*Dq**2))
    e_t1f = 0.5 * (15*B - 12*Dq - term)
    e_t1p = 0.5 * (15*B - 12*Dq + term)
    e_t2 = 6 * Dq
    
    nu1 = e_t2 - e_t1f
    nu2 = e_t1p - e_t1f
    
    return [nu1 - 17500, nu2 - 25000]

Dq_init, B_init = 1500, 600
sol = fsolve(equations, [Dq_init, B_init])
print(f"Dq: {sol[0]}, B: {sol[1]}")
