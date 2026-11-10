import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    tenDq = 10 * Dq
    
    # Energy of 4A2g relative to CF center of gravity
    E_A2g = -1.2 * tenDq
    
    # Matrix for 4T1g states relative to CF center of gravity
    mat = np.array([[1.0 * tenDq, np.sqrt(120*B*tenDq)],
                    [np.sqrt(120*B*tenDq), 15*B + 1.0 * tenDq]])
    eigvals = np.linalg.eigvalsh(mat)
    
    nu1_calc = tenDq # ( -0.2*tenDq ) - ( -1.2*tenDq )
    nu2_calc = eigvals[0] - E_A2g
    nu3_calc = eigvals[1] - E_A2g
    
    return [nu1_calc - 12300, nu2_calc - 18500, nu3_calc - 27900]

# Since it's overdetermined, let's use nu1 and nu2 and check nu3.
def equations_2(vars):
    Dq, B = vars
    tenDq = 10 * Dq
    E_A2g = -1.2 * tenDq
    mat = np.array([[1.0 * tenDq, np.sqrt(120*B*tenDq)],
                    [np.sqrt(120*B*tenDq), 15*B + 1.0 * tenDq]])
    eigvals = np.linalg.eigvalsh(mat)
    return [tenDq - 12300, eigvals[0] - E_A2g - 18500]

sol = fsolve(equations_2, [1230, 700])
print(f"Dq: {sol[0]}, B: {sol[1]}")
tenDq = 10 * sol[0]
E_A2g = -1.2 * tenDq
mat = np.array([[1.0 * tenDq, np.sqrt(120*sol[1]*tenDq)],
                [np.sqrt(120*sol[1]*tenDq), 15*sol[1] + 1.0 * tenDq]])
eigvals = np.linalg.eigvalsh(mat)
print(f"nu1: {tenDq}, nu2: {eigvals[0] - E_A2g}, nu3: {eigvals[1] - E_A2g}")
