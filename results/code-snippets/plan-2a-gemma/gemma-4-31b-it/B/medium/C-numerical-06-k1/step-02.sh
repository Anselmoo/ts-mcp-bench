cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    Delta = 10 * Dq
    v1_obs, v2_obs, v3_obs = 9180, 19550, 20320
    
    # E(4T2g) = 0.5 * Delta
    # E(4A2g) = 1.5 * Delta + 6*B
    # T1g states roots of E^2 + (Delta - 15*B)E + (0.25*Delta^2 - 7.5*B*Delta - 36*B^2) = 0
    a = 1
    b = Delta - 15*B
    c = 0.25*Delta**2 - 7.5*B*Delta - 36*B**2
    
    disc = b**2 - 4*a*c
    if disc < 0: return 1e12
    sqrt_disc = np.sqrt(disc)
    e_t1g_f = (-b - sqrt_disc) / 2
    e_t1g_p = (-b + sqrt_disc) / 2
    e_t2g = 0.5 * Delta
    e_a2g = 1.5 * Delta + 6*B
    
    v1 = e_t2g - e_t1g_f
    v2 = e_a2g - e_t1g_f
    v3 = e_t1g_p - e_t1g_f
    
    return (v1 - v1_obs)**2 + (v2 - v2_obs)**2 + (v3 - v3_obs)**2

res = minimize(objective, [600, 1000], method='Nelder-Mead')
print(res.x)
EOF
python3 solution.py
