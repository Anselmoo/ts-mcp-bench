import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    tenDq = 10 * Dq
    
    # Energies relative to 4A2g
    # nu1 = 10Dq
    nu1_calc = tenDq
    
    # For 4T1g states, we solve the 2x2 matrix:
    # [ 15B + 10Dq,  sqrt(120B*10Dq) ]
    # [ sqrt(120B*10Dq), 30B + 10Dq ]
    # This is a common form, but let's verify the elements.
    # Actually, the matrix for d3 4T1g states is:
    # H = [ 15B + 10Dq,  sqrt(120B*10Dq) ]
    #     [ sqrt(120B*10Dq), 30B + 10Dq ]
    # Let's test this.
    
    mat = np.array([[15*B + tenDq, np.sqrt(120*B*tenDq)],
                    [np.sqrt(120*B*tenDq), 30*B + tenDq]])
    eigvals = np.linalg.eigvalsh(mat)
    
    nu2_calc = eigvals[0]
    nu3_calc = eigvals[1]
    
    return [nu1_calc - 12300, nu2_calc - 18500, nu3_calc - 27900]

# We have 3 equations and 2 variables. This might be overdetermined.
# But the prompt gives 3 bands. Let's see if B and Dq can fit them.
# Let's try to solve using only nu1 and nu2.
def equations_2(vars):
    Dq, B = vars
    tenDq = 10 * Dq
    mat = np.array([[15*B + tenDq, np.sqrt(120*B*tenDq)],
                    [np.sqrt(120*B*tenDq), 30*B + tenDq]])
    eigvals = np.linalg.eigvalsh(mat)
    return [tenDq - 12300, eigvals[0] - 18500]

sol = fsolve(equations_2, [1230, 700])
print(f"Dq: {sol[0]}, B: {sol[1]}")
# Now check nu3
tenDq = 10 * sol[0]
mat = np.array([[15*sol[1] + tenDq, np.sqrt(120*sol[1]*tenDq)],
                [np.sqrt(120*sol[1]*tenDq), 30*sol[1] + tenDq]])
eigvals = np.linalg.eigvalsh(mat)
print(f"nu1: {tenDq}, nu2: {eigvals[0]}, nu3: {eigvals[1]}")
