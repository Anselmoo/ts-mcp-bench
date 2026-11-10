cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2, nu3):
    Dq, B = vars
    # For d3 (Oh) or d7 (Td), the energies are:
    # nu1 = 10 Dq
    # nu2 and nu3 are eigenvalues of:
    # [ 20*Dq, 6*B ]
    # [ 6*B, 12*Dq + 15*B ]
    # (Note: these are relative to the ground state 4A2)
    
    # Let's check the matrix again. 
    # The unperturbed energy of 4T1(F) relative to 4A2 is 20 Dq.
    # The unperturbed energy of 4T1(P) relative to 4A2 is 12 Dq + 15 B.
    # The mixing is 6 B.
    
    mat = np.array([[20*Dq, 6*B], [6*B, 12*Dq + 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    
    return [
        10*Dq - nu1,
        eigvals[0] - nu2,
        eigvals[1] - nu3
    ]

# Since we have 3 equations and 2 variables, the system might be overdetermined
# or nu1=10Dq might be a good starting point.
nu1, nu2, nu3 = 4330, 7520, 18640

# Guess
Dq_guess = nu1 / 10
B_guess = 600

# We can't use fsolve for 3 eqs 2 vars. 
# Let's try to find Dq and B that minimize the sum of squares.
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    mat = np.array([[20*Dq, 6*B], [6*B, 12*Dq + 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    return (10*Dq - nu1)**2 + (eigvals[0] - nu2)**2 + (eigvals[1] - nu3)**2

res = minimize(objective, [Dq_guess, B_guess])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")

# Let's verify the results
Dq, B = res.x
mat = np.array([[20*Dq, 6*B], [6*B, 12*Dq + 15*B]])
eigvals = np.linalg.eigvalsh(mat)
print(f"Predicted bands: {10*Dq}, {eigvals[0]}, {eigvals[1]}")
EOF
python3 solver.py
