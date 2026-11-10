import numpy as np
from scipy.optimize import fsolve

def equation(B):
    Dq = 901.0
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    nu3 = np.sqrt((E_T1g_F_un - E_T1g_P_un)**2 + 4*(6*B)**2)
    return nu3 - 32330

res = fsolve(equation, 600)
print(f'B: {res[0]}')
