import numpy as np
from scipy.optimize import fsolve

def get_nu1_nu2(p):
    Dq, B = p
    # nu1 = 0.5 * (10*Dq - 3*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    # nu2 = 0.5 * (10*Dq + 27*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    # Let's use a more standard form:
    # E(3T1_F) = -0.5 * (15*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    # E(3T2) = 10*Dq - 1.5*B
    # E(3T1_P) = 0.5 * (15*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2)) + 15*B - 10*Dq ? No.
    # Let's use the ones that worked:
    v1 = 0.5 * (10*Dq - 3*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    v2 = 0.5 * (10*Dq + 27*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    return v1, v2

def solve():
    nu1, nu2 = 17500, 25000
    def eqs(p):
        v1, v2 = get_nu1_nu2(p)
        return [v1 - nu1, v2 - nu2]
    Dq, B = fsolve(eqs, [1700, 600])
    return Dq, B

Dq, B = solve()
print(f"Dq = {Dq:.2f}, B = {B:.2f}")
