cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    term = np.sqrt((15*B)**2 + 1440*Dq**2)
    e_t1f = 0.5 * (15*B - term)
    nu1 = 10*Dq - e_t1f
    nu2 = term
    return [nu1 - 17500, nu2 - 25000]

sol = fsolve(equations, [1500, 800])
print(f"Dq: {sol[0]}, B: {sol[1]}")
EOF
python3 solver.py
