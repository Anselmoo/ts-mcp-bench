cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p, nu1, nu2):
    Dq, B = p
    v1 = 0.5 * (10*Dq - 3*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    v2 = 0.5 * (10*Dq + 27*B + np.sqrt(100*Dq**2 + 120*B*Dq + 9*B**2))
    return [v1 - nu1, v2 - nu2]

nu1 = 17500
nu2 = 25000
Dq, B = fsolve(equations, [1700, 600], args=(nu1, nu2))
print(f"Dq = {Dq:.2f}, B = {B:.2f}")
EOF
python3 solver.py
