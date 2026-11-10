cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    # The energies of the 4T1g states are roots of the secular determinant
    # For d3, relative to 4A2g:
    # Matrix = [[15*Dq - 15*B, sqrt(120)*Dq], [sqrt(120)*Dq, 15*B]]
    # Wait, let's use a better matrix from a reliable source:
    # E(4A2g) = -15B
    # E(4T2g) = -15B + 10Dq
    # E(4T1g_F) = -15B + 15Dq
    # E(4T1g_P) = 15B
    # The 4T1g states are the eigenvalues of:
    # [[15*Dq, sqrt(120)*Dq], [sqrt(120)*Dq, 30*B]] relative to 4A2g?
    # Let's try:
    # matrix = [[15*Dq, np.sqrt(120)*Dq], [np.sqrt(120)*Dq, 30*B]]
    # evals = np.linalg.eigvals(matrix)
    # return [nu1 - 14490, evals[0] - 20430, evals[1] - 32030]
    # That's 3 eq for 2 var. Let's use nu1=10Dq and nu2, nu3.
    pass

# Let's just solve for B using nu2 and nu3 given Dq = 1449.
Dq = 1449
nu2_obs = 20430
nu3_obs = 32030

def find_B(B):
    # Matrix for 4T1g states relative to 4A2g:
    # The 4T1g(F) energy relative to 4A2g is 15Dq.
    # The 4T1g(P) energy relative to 4A2g is 30B (since 15B - (-15B) = 30B).
    # The interaction is sqrt(120)Dq.
    matrix = np.array([[15*Dq, np.sqrt(120)*Dq], [np.sqrt(120)*Dq, 30*B]])
    evals = np.linalg.eigvals(matrix)
    evals = np.sort(evals)
    return evals[0] - nu2_obs, evals[1] - nu3_obs

from scipy.optimize import fsolve
B_sol = fsolve(lambda B: find_B(B)[0], 600)[0]
print(f"B = {B_sol}")
evals_final = np.linalg.eigvals(np.array([[15*Dq, np.sqrt(120)*Dq], [np.sqrt(120)*Dq, 30*B_sol]]))
print(f"Evals = {np.sort(evals_final)}")
EOF
python3 solver.py
