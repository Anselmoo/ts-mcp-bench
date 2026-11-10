cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    # Standard T1g matrix for d2 Octahedral
    # H = [[-4Dq, sqrt(480)B], [sqrt(480)B, 15B - 4Dq]]
    # Trace = 15B - 8Dq
    # Det = -60BDq + 16Dq^2 - 480B^2
    # eigenvalues = [Trace +/- sqrt(Trace^2 - 4Det)] / 2
    # Trace^2 - 4Det = (15B-8Dq)^2 - 4(-60BDq + 16Dq^2 - 480B^2) = 2145B^2
    
    x1 = (15*B - 8*Dq - np.sqrt(2145)*B) / 2
    x2 = (15*B - 8*Dq + np.sqrt(2145)*B) / 2
    
    e_t2g = -3*Dq
    e_a2g = 12*Dq
    
    # Try all permutations of (T2g, T1gP, A2g)
    import itertools
    best_err = float('inf')
    best_vals = None
    
    transitions = [e_t2g - x1, x2 - x1, e_a2g - x1]
    # Since we want to match [15730, 24030, 32750]
    # we just sort them.
    calc = sorted(transitions)
    return np.array(calc)

def objective(params):
    nu_obs = np.array([15730, 24030, 32750])
    nu_calc = get_energies(params)
    return np.sum((nu_obs - nu_calc)**2)

res = minimize(objective, [1000, 600], bounds=[(0, 5000), (0, 5000)])
print(f"Dq={res.x[0]:.2f}, B={res.x[1]:.2f}")
print(f"Calculated: {get_energies(res.x)}")
EOF
python3 solver.py
