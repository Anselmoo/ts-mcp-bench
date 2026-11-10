cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    Delta = 10 * Dq
    v1_obs, v2_obs, v3_obs = 9180, 19550, 20320
    
    # T1g roots
    term = (15*B - Delta)**2 + 24*B*Delta
    if term < 0: return 1e12
    sqrt_term = np.sqrt(term)
    e_t1g_f = 0.5 * (15*B - Delta - sqrt_term)
    e_t1g_p = 0.5 * (15*B - Delta + sqrt_term)
    e_t2g = 0.5 * Delta
    e_a2g = 1.5 * Delta + 6*B
    
    v1 = e_t2g - e_t1g_f
    v2 = e_a2g - e_t1g_f
    v3 = e_t1g_p - e_t1g_f
    
    return (v1 - v1_obs)**2 + (v2 - v2_obs)**2 + (v3 - v3_obs)**2

res = minimize(objective, [1000, 800], method='Nelder-Mead')
print(res.x)
EOF
python3 solution.py
