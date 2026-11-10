cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    # 4T1g states are roots of x^2 - (30Dq + 15B)x + (200Dq^2 + 150DqB) = 0 ?
    # No, let's use the secular determinant:
    # det[[15Dq - nu, sqrt(120)Dq], [sqrt(120)Dq, 15B + 15Dq - nu]] = 0
    # (15Dq - nu)(15B + 15Dq - nu) - 120Dq^2 = 0
    # nu^2 - (30Dq + 15B)nu + 15Dq(15B + 15Dq) - 120Dq^2 = 0
    # nu^2 - (30Dq + 15B)nu + 225DqB + 225Dq^2 - 120Dq^2 = 0
    # nu^2 - (30Dq + 15B)nu + 225DqB + 105Dq^2 = 0
    
    # Let's solve this quadratic for nu:
    # nu = [ (30Dq + 15B) +/- sqrt((30Dq + 15B)^2 - 4(225DqB + 105Dq^2)) ] / 2
    
    term1 = 30*Dq + 15*B
    term2 = np.sqrt(term1**2 - 4*(225*Dq*B + 105*Dq**2))
    nu2 = (term1 - term2) / 2
    nu3 = (term1 + term2) / 2
    
    return [nu1 - 14490, nu2 - 20430, nu3 - 32030]

# We have 3 equations for 2 variables. This might be overdetermined.
# Let's see if a solution exists.
from scipy.optimize import least_squares
res = least_squares(equations, [1449, 600])
print(f"Dq = {res.x[0]}, B = {res.x[1]}")
print(f"Residuals = {res.fun}")
EOF
python3 solver.py
