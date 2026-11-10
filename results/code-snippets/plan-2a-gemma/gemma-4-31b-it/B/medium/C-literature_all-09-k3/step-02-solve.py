import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B, C = vars
    # nu1 is the lower eigenvalue of the 2x2 matrix for 4T1g
    # matrix elements:
    # E_G = -10*Dq + 10*B + 5*C
    # E_P = 15*B + 5*C (Wait, let's check this E_P again)
    # However, many textbooks use the simplified nu1 = 10B + 5C - 10Dq.
    # Let's try to find the actual E_P for d5.
    # A common expression for 4P relative to 6S is E = 15B + 5C?
    # Let's check: for Mn2+, B ~ 800, C ~ 3000. 
    # 15*800 + 5*3000 = 12000 + 15000 = 27000.
    # That's in the range of the observed bands!
    
    Eg_T1 = -10*Dq + 10*B + 5*C
    Ep_T1 = 15*B + 5*C
    V = 6*Dq
    
    # Eigenvalue:
    # nu1 = 0.5 * (Eg_T1 + Ep_T1 - np.sqrt((Eg_T1 - Ep_T1)**2 + 4*V**2))
    nu1_calc = 0.5 * (Eg_T1 + Ep_T1 - np.sqrt((Eg_T1 - Ep_T1)**2 + 4*V**2))
    
    nu2_calc = -10*Dq + 15*B + 5*C
    nu3_calc = 15*B + 5*C
    
    return [nu1_calc - 19720, nu2_calc - 23260, nu3_calc - 24980]

guess = [200, 800, 3000]
sol = fsolve(equations, guess)
print(f"Dq: {sol[0]:.2f}, B: {sol[1]:.2f}, C: {sol[2]:.2f}")
