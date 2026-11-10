import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    # d3 Oh / d7 Td
    # E(4A2) = 0
    # E(4T2) = 10 * Dq
    # For 4T1 states, use the matrix:
    # Matrix elements based on standard ligand field theory for d3
    # The 4T1 states mix. The matrix in the basis of |4T1(F)> and |4T1(P)> is:
    # H = [[-10*Dq, sqrt(120)*Dq], [sqrt(120)*Dq, 15*B + 20*Dq]] 
    # Wait, let me check this matrix again.
    # A common matrix for d3 T1 states is:
    # E1 = -10*Dq
    # E2 = 15*B + 20*Dq
    # V = sqrt(120)*Dq
    # This is from some lecture notes. Let's test it.
    
    # Let's try this one:
    # E(4A2) = 0
    # E(4T2) = 10*Dq
    # The two 4T1 states are eigenvalues of:
    # [[-10*Dq, sqrt(120)*Dq], [sqrt(120)*Dq, 15*B + 20*Dq]]
    # Let's check Dq=0: eigenvalues 0 and 15B. Correct.
    
    mat = np.array([[-10*Dq, np.sqrt(120)*Dq], [np.sqrt(120)*Dq, 15*B + 20*Dq]])
    evals = np.linalg.eigvalsh(mat)
    
    return np.array([10*Dq, evals[0], evals[1]])

def objective(params):
    target = np.array([4070, 7030, 16400])
    calc = get_energies(params)
    return np.sum((target - calc)**2)

res = minimize(objective, [400, 800], bounds=[(0, 2000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Calculated: {get_energies(res.x)}")
