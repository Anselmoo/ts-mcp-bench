cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    # d8 octahedral energies relative to 3A2
    # Nu1 = 10 Dq
    # Nu2 and Nu3 are eigenvalues of the matrix:
    # [[ 18*Dq, 18*B ],
    #  [ 18*B, 12*Dq + 15*B ]]
    # Wait, I need the correct matrix.
    # Let's try the common matrix:
    # [[ 18*Dq, 6*sqrt(10)*B ],
    #  [ 6*sqrt(10)*B, 12*Dq + 15*B ]]
    # No, let's use:
    # E(3T1) = 0.5 * ( (18*Dq + 12*Dq + 15*B) +/- sqrt((18*Dq - (12*Dq + 15*B))**2 + 4*V**2) )
    # V = 18*B is common in some texts, V = 6*sqrt(10)*B in others.
    
    V = 18 * B 
    E1 = 18 * Dq
    E2 = 12 * Dq + 15 * B
    
    # eigenvalues
    diff = (E1 - E2) / 2
    term = np.sqrt(diff**2 + V**2)
    nu2 = (E1 + E2) / 2 - term
    nu3 = (E1 + E2) / 2 + term
    
    # target values
    nu1_target = 9770
    nu2_target = 16050
    nu3_target = 26740
    
    return [10*Dq - nu1_target, nu2 - nu2_target]

# This depends on the mixing V. Let's test different V.
EOF
python3 solution.py
