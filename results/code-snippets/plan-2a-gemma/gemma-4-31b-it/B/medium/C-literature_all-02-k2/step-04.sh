cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2):
    Dq, B = vars
    coupling = np.sqrt(180) * B
    # Matrix for T1 states relative to 3F barycenter
    # H = [[0, coupling], [coupling, 30*B + 10*Dq]]
    eigvals = np.linalg.eigvalsh([[0, coupling], [coupling, 30*B + 10*Dq]])
    E_low = eigvals[0]
    E_high = eigvals[1]
    
    nu1_calc = 10*Dq - E_low
    nu2_calc = E_high - E_low
    return [nu1_calc - nu1, nu2_calc - nu2]

nu1 = 17500
nu2 = 25000
sol = fsolve(equations, [1800, 800], args=(nu1, nu2))
print(f"Dq: {sol[0]}, B: {sol[1]}")
EOF
python3 solver.py
