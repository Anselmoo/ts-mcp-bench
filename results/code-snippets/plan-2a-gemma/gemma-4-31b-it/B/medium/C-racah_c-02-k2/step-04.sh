cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    term1 = 45*B + 15*Dq
    term2 = np.sqrt((15*B - 15*Dq)**2 + 120*Dq*B)
    nu2 = (term1 - term2) / 2
    nu3 = (term1 + term2) / 2
    return [nu1 - 14490, nu2 - 20430, nu3 - 32030]

from scipy.optimize import least_squares
res = least_squares(equations, [1449, 600])
print(f"Dq = {res.x[0]}, B = {res.x[1]}")
EOF
python3 solver.py
