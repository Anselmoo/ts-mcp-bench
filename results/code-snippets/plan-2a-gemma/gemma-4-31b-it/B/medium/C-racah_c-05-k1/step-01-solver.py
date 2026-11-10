import numpy as np
from scipy.optimize import fsolve

def energies(Dq, B):
    # v1 = 10*Dq
    v1 = 10 * Dq
    
    # v2 and v3 are the eigenvalues of the matrix:
    # [ 15*Dq - 15*B , 6*sqrt(10)*B ]
    # [ 6*sqrt(10)*B , 15*B - 15*B ]
    # No, that's not right.
    # Let's use the standard matrices for d3.
    # Energy relative to 4A2g:
    # 4T2g: 10 Dq
    # 4T1g(F) and 4T1g(P) are eigenvalues of:
    # H = [[15*Dq, 6*sqrt(10)*B], [6*sqrt(10)*B, 15*B]] - No.
    # Let's use the correct matrix for d3:
    # Relative to 4A2g:
    # E(4T2g) = 10 Dq
    # E(4T1g) are eigenvalues of:
    # [[ 15*Dq - 5*B, 6*sqrt(10)*B ],
    #  [ 6*sqrt(10)*B, 15*B ]] - Wait, let's check.
    
    # Correct matrix for d3 4T1g states relative to 4A2g:
    # Matrix = [[ 15*Dq, 6*sqrt(10)*B ], [ 6*sqrt(10)*B, 15*B ]]
    # This is for the case where 4A2g is the origin.
    # Let's try:
    matrix = np.array([[15*Dq, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B]])
    eigvals = np.linalg.eigvalsh(matrix)
    return v1, eigvals[0], eigvals[1]

def objective(params):
    Dq, B = params
    v1, v2, v3 = energies(Dq, B)
    return [v1 - 17500, v2 - 23860, v3 - 37910]

# Since we have 3 equations and 2 unknowns, we can't solve it exactly unless it's consistent.
# But v1 = 10*Dq is very direct.
Dq_fixed = 17500 / 10
def objective_B(B):
    v1, v2, v3 = energies(Dq_fixed, B)
    # We have two more transitions. Let's see which one fits B better.
    return v2 - 23860

B_sol = fsolve(objective_B, 600)[0]
v1, v2, v3 = energies(Dq_fixed, B_sol)
print(f"Dq: {Dq_fixed}, B: {B_sol}")
print(f"v1: {v1}, v2: {v2}, v3: {v3}")
