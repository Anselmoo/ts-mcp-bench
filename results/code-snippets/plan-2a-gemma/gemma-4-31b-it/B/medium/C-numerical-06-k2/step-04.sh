cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Delta, B = params # Delta is 10*Dq
    if Delta <= 0 or B <= 0: return 1e10
    
    # Use d3 formulas but with -Delta
    # E(A2g) = 0
    # E(T2g) = -Delta
    # T1g matrix:
    mat = np.array([[15*B - (-Delta), 6*B], [6*B, 15*B]])
    eigs = np.linalg.eigvalsh(mat)
    e_t1g_low = eigs[0]
    e_t1g_high = eigs[1]
    e_t2g = -Delta
    e_a2g = 0
    
    # For d7 HS, the ground state is the lowest of these
    all_e = np.array([e_t1g_low, e_t2g, e_a2g, e_t1g_high])
    sorted_e = np.sort(all_e)
    
    v1 = sorted_e[1] - sorted_e[0]
    v2 = sorted_e[2] - sorted_e[0]
    v3 = sorted_e[3] - sorted_e[0]
    
    target = np.array([9180, 19550, 20320])
    return np.sum((np.array([v1, v2, v3]) - target)**2)

res = minimize(objective, [10000, 1000], method='Nelder-Mead')
print(f"10Dq: {res.x[0]:.2f}, B: {res.x[1]:.2f}")
EOF
python3 solver.py
