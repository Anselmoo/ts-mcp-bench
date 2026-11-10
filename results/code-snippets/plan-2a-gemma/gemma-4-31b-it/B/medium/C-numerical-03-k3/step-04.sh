cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    Delta = 10 * Dq
    
    term1 = 15 * B - Delta
    term2 = (15 * B + Delta)**2 + 144 * B**2
    
    e_t1f = (term1 - np.sqrt(term2)) / 2
    e_t1p = (term1 + np.sqrt(term2)) / 2
    e_t2g = Delta
    e_a2g = 3 * Delta
    
    nu1 = e_t2g - e_t1f
    nu2 = e_t1p - e_t1f
    nu3 = e_a2g - e_t1f
    
    obs = np.array([15490, 24500, 32330])
    calc = np.array([nu1, nu2, nu3])
    return np.sum((obs - calc)**2)

for dq_start in [500, 800, 1100]:
    for b_start in [400, 600, 800, 1000]:
        res = minimize(objective, [dq_start, b_start], method='Nelder-Mead')
        print(f"Start: {dq_start}, {b_start} -> Dq: {res.x[0]:.2f}, B: {res.x[1]:.2f}, Error: {res.fun:.2f}")
EOF
python3 solver.py
