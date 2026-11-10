import numpy as np

B = 612.7
Dq = 1684.0
E_T2g = 10*Dq - 3*B
E_A2g = 20*Dq - 3*B
E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
E_T1g_P_un = 15*B
trace = E_T1g_F_un + E_T1g_P_un
det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
disc = np.sqrt(trace**2 - 4*det)
E_ground = 0.5 * (trace - disc)
E_T1g_P = 0.5 * (trace + disc)
print(f'nu1: {E_T2g - E_ground}')
print(f'nu2: {E_T1g_P - E_ground}')
print(f'nu3: {E_A2g - E_ground}')
