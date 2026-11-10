cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def objective(vars):
    B, Dq = vars
    nu1_calc = 10 * Dq
    term = np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)
    nu2_calc = 0.5 * (45*B + 10*Dq - term)
    nu3_calc = 0.5 * (45*B + 10*Dq + term)
    
    nu1_obs, nu2_obs, nu3_obs = 14170, 21710, 33970
    return (nu1_calc - nu1_obs)**2 + (nu2_calc - nu2_obs)**2 + (nu3_calc - nu3_obs)**2

res = minimize(objective, [900, 1417])
B_sol, Dq_sol = res.x
print(f"B = {B_sol}, Dq = {Dq_sol}")
EOF
python3 solution.py
