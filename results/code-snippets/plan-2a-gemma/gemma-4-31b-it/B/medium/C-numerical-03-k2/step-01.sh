cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def calculate_energies(params):
    Dq, B = params
    # For d2 octahedral, the states are 3T1g(F), 3T2g, 3A2g, 3T1g(P)
    # We use the matrix for 3T1g mixing
    # Energy of 3T2g and 3A2g relative to a chosen origin
    # E(3T2g) = 10*Dq - 15*B
    # E(3A2g) = 20*Dq - 15*B
    # The 3T1g states are eigenvalues of the matrix:
    # [ [ -15*B + 15*Dq, 6*B ],
    #   [ 6*B, 15*B + 15*Dq ] ]
    # Wait, let's use the formula for the 3T1g matrix from a reliable source
    # The matrix for 3T1g (relative to 3F barycenter) is:
    # H = [[ 15*Dq - 15*B, 6*B ], [ 6*B, 15*Dq + 15*B ]]
    # No, that's what I used before.
    # Let's use:
    # E(3T2g) = 10*Dq - 15*B
    # E(3A2g) = 20*Dq - 15*B
    # and E(3T1g) = eigenvalue of [[ 0, 6*B ], [ 6*B, 30*B + 10*Dq ]]? No.
    
    # Let's use the following transition formulas for d2 (common approximations):
    # nu1 = 10*Dq - 4*B
    # nu2 = 15*Dq + 5*B
    # nu3 = 20*Dq - 10*B
    # Let's try to fit these first.
    return np.array([10*Dq - 4*B, 15*Dq + 5*B, 20*Dq - 10*B])

def objective(params):
    obs = np.array([15490, 24500, 32330])
    calc = calculate_energies(params)
    return np.sum((obs - calc)**2)

res = minimize(objective, [1600, 600], bounds=[(0, None), (0, None)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
EOF
python3 solution.py
