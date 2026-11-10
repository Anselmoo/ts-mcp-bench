cat << 'EOF' > solve_dq_b.py
import numpy as np
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    term = np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    e_t1g_f = 0.5 * (15*B + 10*Dq - term)
    e_t1g_p = 0.5 * (15*B + 10*Dq + term)
    
    # Transitions for d7 high spin
    v = [
        10*Dq - e_t1g_f,
        -e_t1g_f, # This is the problem
        e_t1g_p - e_t1g_f
    ]
    # Let's try to just use the differences between the states
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # E(A2g) - E(T2g) = 10*Dq
    # E(T1g_P) - E(T1g_F) = term
    
    v1 = 10*Dq - e_t1g_f
    v2 = v1 + 10*Dq
    v3 = term
    
    targets = [9180, 19550, 20320]
    return (v1-targets[0])**2 + (v2-targets[1])**2 + (v3-targets[2])**2

res = minimize(objective, [1000, 800], bounds=[(0, 5000), (0, 5000)])
print(res.x)
EOF
python3 solve_dq_b.py
