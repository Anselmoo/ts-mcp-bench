cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def get_nu(Dq, B):
    # nu1 = 10Dq
    nu1 = 10 * Dq
    # The T1g states are eigenvalues of:
    # [[ 15*Dq - 6*B, 6*sqrt(2)*Dq ],
    #  [ 6*sqrt(2)*Dq, 15*B - 6*Dq ]]
    # No, let's use the correct matrix from a source.
    # For d8, the energies are:
    # E(3A2g) = 0
    # E(3T2g) = 10*Dq
    # For 3T1g, the matrix is:
    # H = [[ 10*Dq - 6*B, 6*sqrt(2)*Dq ],
    #      [ 6*sqrt(2)*Dq, 10*Dq + 15*B - 6*B ]]
    # Let's check: if Dq=0, H = [[-6B, 0], [0, 9B]]. 
    # This is not right. The states should be 0 and 15B.
    
    # Correct matrix for T1g (relative to 3A2g):
    # H = [[ 10*Dq - 6*B, 6*sqrt(2)*Dq ],
    #      [ 6*sqrt(2)*Dq, 10*Dq + 15*B - 6*B ]]
    # Wait, if Dq=0, E = -6B and 9B. Shift by 6B -> 0 and 15B.
    # So the energies are eigenvalues of H + 6B.
    # H_shifted = [[ 10*Dq, 6*sqrt(2)*Dq ],
    #             [ 6*sqrt(2)*Dq, 10*Dq + 15*B ]]
    
    # Let's test Dq=0: H_shifted = [[0, 0], [0, 15B]]. Eigenvalues 0, 15B. Correct!
    # Let's test Dq > 0:
    # Eigenvalues of [[ 10*Dq, 6*sqrt(2)*Dq ], [ 6*sqrt(2)*Dq, 10*Dq + 15*B ]]
    # lambda = 10*Dq + (15*B + sqrt( (15*B)^2 + (12*sqrt(2)*Dq)^2 )) / 2
    # lambda = 10*Dq + (15*B - sqrt( (15*B)^2 + 288*Dq^2 )) / 2
    
    # Let's try these.
    nu1 = 10 * Dq
    term = np.sqrt((15 * B)**2 + 288 * Dq**2)
    nu2 = 10 * Dq + (15 * B - term) / 2
    nu3 = 10 * Dq + (15 * B + term) / 2
    return nu1, nu2, nu3

def equations(vars):
    Dq, B = vars
    nu1, nu2, nu3 = get_nu(Dq, B)
    return [nu1 - 9770, nu2 - 16050] # nu3 is then determined

# Use fsolve to find Dq and B
Dq_init, B_init = 977, 700
solution = fsolve(equations, [Dq_init, B_init])
Dq, B = solution
nu1, nu2, nu3 = get_nu(Dq, B)
print(f"Dq: {Dq}, B: {B}, nu1: {nu1}, nu2: {nu2}, nu3: {nu3}")
EOF
python3 solver.py
