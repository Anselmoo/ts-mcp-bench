cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    Delta_o = 10 * Dq
    # Matrix for T1g states relative to barycenter
    # H = [[-0.5*Delta_o - 6*B, 6*B], [6*B, 0.5*Delta_o - 15*B]]
    # This is from a source. Let's check it.
    # If Delta_o=0, eigenvalues are -6B +/- sqrt(0 + 36B^2) = 0 and -12B? No.
    # At Delta_o=0, T1g(F) should be 0 and T1g(P) should be 15B.
    # The matrix should be:
    # [[0, 0], [0, 15*B]]? No, because of mixing.
    # The mixing is 6B.
    # H = [[0, 6*B], [6*B, 15*B]]
    # eigenvalues: det(H-L) = -L(15B-L) - 36B^2 = L^2 - 15BL - 36B^2 = 0
    # L = (15B +/- sqrt(225B^2 + 144B^2))/2 = (15B +/- 19.2B)/2
    # L1 = -2.1B, L2 = 17.1B.
    # This is close to 0 and 15B.
    
    # Now add Delta_o.
    # T1g(F) is -0.5*Delta_o. T1g(P) is 0.5*Delta_o.
    # H = [[-0.5*Delta_o, 6*B], [6*B, 0.5*Delta_o + 15*B]]
    # eigenvalues: det(H-L) = (-0.5*Delta_o - L)(0.5*Delta_o + 15*B - L) - 36*B^2 = 0
    # L^2 - L(15*B) - 0.5*Delta_o(0.5*Delta_o + 15*B) - 36*B^2 = 0? No.
    # L^2 - L(15*B) - 0.25*Delta_o^2 - 7.5*Delta_o*B - 36*B^2 = 0
    # L = (15*B +/- sqrt(225*B^2 + 4(0.25*Delta_o^2 + 7.5*Delta_o*B + 36*B^2)))/2
    # L = (15*B +/- sqrt(225*B^2 + Delta_o^2 + 30*Delta_o*B + 144*B^2))/2
    # L = (15*B +/- sqrt(Delta_o^2 + 30*Delta_o*B + 369*B^2))/2
    
    L1 = (15*B - np.sqrt(Delta_o**2 + 30*Delta_o*B + 369*B**2)) / 2
    L2 = (15*B + np.sqrt(Delta_o**2 + 30*Delta_o*B + 369*B**2)) / 2
    
    # E(4T2g) = -0.5*Delta_o + 6*B  (Relative to barycenter)
    # E(4A2g) = 0*Delta_o + 6*B
    # nu1 = E(4T2g) - L1
    # nu2 = E(4A2g) - L1
    # nu3 = L2 - L1
    
    return np.array([
        -0.5*Delta_o + 6*B - L1,
        6*B - L1,
        L2 - L1
    ])

def objective(params):
    obs = np.array([9460, 20160, 21160])
    calc = get_energies(params)
    return np.sum((obs - calc)**2)

res = minimize(objective, [1000, 800], bounds=[(100, 5000), (100, 2000)])
print(res.x)
EOF
python3 solver.py
