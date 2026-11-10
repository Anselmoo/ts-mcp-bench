cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    B, Dq = vars
    # Transition energies relative to 6A1g
    # Nu1: lower 4T1
    # Nu2: 4T2
    # Nu3: 4E, 4A1
    
    # Energy of 4G states relative to 6S (ground)
    # In many textbooks:
    # E(4G) = 10B
    # E(4P) = 15B
    # Let's assume these are relative to 6S.
    
    # In the octahedral field:
    # 6A1g is 0 (since t2g^3 eg^2 = 3*(-4Dq) + 2*(6Dq) = 0)
    # 4G splits into:
    # E(4T1_G) = 10B - 10Dq
    # E(4T2_G) = 10B - 5Dq
    # E(4E_G, 4A1_G) = 10B
    # 4P becomes:
    # E(4T1_P) = 15B
    
    # The two 4T1 states mix:
    # Matrix = [[10*B - 10*Dq, 6*B], [6*B, 15*B]]
    # Eigenvalues:
    tr = 25*B - 10*Dq
    det = (10*B - 10*Dq)*(15*B) - 36*B**2
    # lambda = (tr - sqrt(tr^2 - 4*det)) / 2
    nu1_calc = 0.5 * (tr - np.sqrt(tr**2 - 4*det))
    nu2_calc = 10*B - 5*Dq
    nu3_calc = 10*B
    
    return [nu1_calc - 19720, nu2_calc - 23260, nu3_calc - 24980]

# Since we have 3 equations and 2 variables, it's overdetermined.
# Let's try to solve using nu2 and nu3 first.
B_start = 2498
Dq_start = 344
print(f"Starting with nu2, nu3: B={B_start}, Dq={Dq_start}")
# Check nu1 for these values
tr = 25*B_start - 10*Dq_start
det = (10*B_start - 10*Dq_start)*(15*B_start) - 36*B_start**2
nu1 = 0.5 * (tr - np.sqrt(tr**2 - 4*det))
print(f"nu1 calc = {nu1}")

# Let's try to find B and Dq that best fit all three.
from scipy.optimize import least_squares
def residuals(vars):
    B, Dq = vars
    tr = 25*B - 10*Dq
    det = (10*B - 10*Dq)*(15*B) - 36*B**2
    nu1_calc = 0.5 * (tr - np.sqrt(tr**2 - 4*det))
    nu2_calc = 10*B - 5*Dq
    nu3_calc = 10*B
    return [nu1_calc - 19720, nu2_calc - 23260, nu3_calc - 24980]

res = least_squares(residuals, [2400, 300])
print(f"Best fit: B={res.x[0]}, Dq={res.x[1]}")
EOF
python3 solver.py
