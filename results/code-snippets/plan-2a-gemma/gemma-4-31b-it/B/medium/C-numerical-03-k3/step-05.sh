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
    
    # New assignment: nu2 = T1g(F) -> A2g, nu3 = T1g(F) -> T1g(P)
    nu1 = e_t2g - e_t1f
    nu2 = e_a2g - e_t1f
    nu3 = e_t1p - e_t1f
    
    obs = np.array([15490, 24500, 32330])
    calc = np.array([nu1, nu2, nu3])
    return np.sum((obs - calc)**2)

res = minimize(objective, [1000, 600], method='Nelder-Mead')
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
EOF
python3 solver.py
