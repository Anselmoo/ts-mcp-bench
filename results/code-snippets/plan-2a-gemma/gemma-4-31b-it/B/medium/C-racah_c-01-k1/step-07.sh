cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def objective(B):
    Dq = 1417.0
    term = np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)
    nu2_calc = 0.5 * (45*B + 10*Dq - term)
    nu3_calc = 0.5 * (45*B + 10*Dq + term)
    
    nu2_obs, nu3_obs = 21710, 33970
    return (nu2_calc - nu2_obs)**2 + (nu3_calc - nu3_obs)**2

res = minimize(objective, [900])
B_sol = res.x[0]
print(f"B = {B_sol}")
EOF
python3 solution.py
