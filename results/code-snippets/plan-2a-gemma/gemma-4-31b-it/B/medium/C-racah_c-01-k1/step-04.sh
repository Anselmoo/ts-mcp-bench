cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    B, Dq = vars
    nu1_calc = 10 * Dq
    term = np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)
    nu2_calc = 0.5 * (45*B + 10*Dq - term)
    nu3_calc = 0.5 * (45*B + 10*Dq + term)
    
    nu1_obs = 14170
    nu2_obs = 21710
    nu3_obs = 33970
    
    return [nu1_calc - nu1_obs, nu2_calc - nu2_obs]

sol = fsolve(equations, [1000, 1417])
B_sol, Dq_sol = sol
term = np.sqrt((15*B_sol - 10*Dq_sol)**2 + 120*B_sol*10*Dq_sol)
nu2_calc = 0.5 * (45*B_sol + 10*Dq_sol - term)
nu3_calc = 0.5 * (45*B_sol + 10*Dq_sol + term)
print(f"B = {B_sol}, Dq = {Dq_sol}, nu2 = {nu2_calc}, nu3 = {nu3_calc}")
EOF
python3 solution.py
