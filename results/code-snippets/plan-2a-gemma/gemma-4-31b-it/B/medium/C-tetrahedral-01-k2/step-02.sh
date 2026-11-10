cat << 'EOF' > solve_lf.py
import numpy as np
from scipy.optimize import minimize

def objective(p):
    Dq, B = p
    v1_calc = 10 * Dq
    # v2 and v3 are the roots of x^2 - (15*B + 30*Dq)x + (15*B + 30*Dq)**2/4 - ((15*B - 10*Dq)**2 + 120*Dq*B)/4 = 0
    # v2 = 0.5 * (15*B + 30*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*Dq*B))
    # v3 = 0.5 * (15*B + 30*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*Dq*B))
    
    # To avoid negative values inside sqrt
    inner = (15*B - 10*Dq)**2 + 120*Dq*B
    if inner < 0: return 1e10
    
    v2_calc = 0.5 * (15*B + 30*Dq - np.sqrt(inner))
    v3_calc = 0.5 * (15*B + 30*Dq + np.sqrt(inner))
    
    return (v1_calc - 4070)**2 + (v2_calc - 7030)**2 + (v3_calc - 16400)**2

res = minimize(objective, [400, 700], method='Nelder-Mead')
print(res.x)
EOF
python3 solve_lf.py
