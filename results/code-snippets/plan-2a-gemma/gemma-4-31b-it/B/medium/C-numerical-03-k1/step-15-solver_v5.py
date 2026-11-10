import numpy as np
from scipy.optimize import fsolve

def equations(p):
    B, Dq = p
    E_T2g = 10*Dq - 3*B
    E_A2g = 20*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    disc = np.sqrt(trace**2 - 4*det)
    E_ground = 0.5 * (trace - disc)
    E_T1g_P = 0.5 * (trace + disc)
    
    return [
        E_T2g - E_ground - 15490,
        E_T1g_P - E_ground - 24500,
        E_A2g - E_ground - 32330
    ]

# This is 3 equations, 2 unknowns. Let's use fsolve on the first two.
def equations_2(p):
    B, Dq = p
    E_T2g = 10*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    disc = np.sqrt(trace**2 - 4*det)
    E_ground = 0.5 * (trace - disc)
    E_T1g_P = 0.5 * (trace + disc)
    return [E_T2g - E_ground - 15490, E_T1g_P - E_ground - 24500]

res = fsolve(equations_2, [600, 1684])
print(f'B: {res[0]}, Dq: {res[1]}')
# Now check nu3
B, Dq = res
E_A2g = 20*Dq - 3*B
E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
E_T1g_P_un = 15*B
trace = E_T1g_F_un + E_T1g_P_un
det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
disc = np.sqrt(trace**2 - 4*det)
E_ground = 0.5 * (trace - disc)
print(f'nu3: {E_A2g - E_ground}')
