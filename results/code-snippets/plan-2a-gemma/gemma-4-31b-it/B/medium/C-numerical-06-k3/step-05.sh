cat << 'EOF' > solve_dq_b.py
import numpy as np
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    term = np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    e_t1g_f = 0.5 * (15*B + 10*Dq - term)
    e_t1g_p = 0.5 * (15*B + 10*Dq + term)
    
    v1 = 10*Dq - e_t1g_f
    v2 = 20*Dq - e_t1g_f
    v3 = e_t1g_p - e_t1g_f
    
    targets = [9180, 19550, 20320]
    # Try different permutations
    best_err = float('inf')
    import itertools
    for p in itertools.permutations(targets):
        err = (v1 - p[0])**2 + (v2 - p[1])**2 + (v3 - p[2])**2
        if err < best_err:
            best_err = err
    return best_err

res = minimize(objective, [1000, 600], bounds=[(0, 5000), (0, 5000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
EOF
python3 solve_dq_b.py
