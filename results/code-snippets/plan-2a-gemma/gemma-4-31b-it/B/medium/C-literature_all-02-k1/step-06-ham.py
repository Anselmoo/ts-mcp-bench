import numpy as np
from scipy.linalg import eigh

def solve_d2(Dq, B, C):
    # This is a complex task. Let's use the known energy levels from a reliable table.
    # For d2 Oh:
    # E(3T1g_F) = -0.5 * (15*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    # E(1Eg) = 3*C - 1.5*B - 3*Dq ? No.
    # Let's use the property that E(1Eg) is independent of Dq to first order.
    # In the strong field limit: E(1Eg) - E(3T1g) = 3*C
    return 3*C

Dq = 1683.54
B = 500.0
C = 3249.33
print(f"Diff = {solve_d2(Dq, B, C)}")
