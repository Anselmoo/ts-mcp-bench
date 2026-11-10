import numpy as np

def get_nu_ratio(x):
    # x = 10Dq / B
    # B = 1
    B = 1.0
    Dq = x / 10.0
    
    # E(T2g) = 10*Dq - 3*B
    # E(A2g) = 20*Dq - 3*B
    # E(T1g,F) = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    # Since B=1, 10Dq = x
    E_T2g = x - 3.0
    E_A2g = 2*x - 3.0
    E_T1g_F = 0.5 * (-15.0 + x - np.sqrt((15.0 - x)**2 + 120.0*x))
    
    nu1 = E_T2g - E_T1g_F
    nu2 = E_A2g - E_T1g_F
    return nu2 / nu1

for x in np.arange(1.0, 20.0, 0.1):
    print(f"x: {x:.1f}, ratio: {get_nu_ratio(x):.3f}")
