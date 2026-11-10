cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    delta = np.sqrt(56.25 * B**2 + 160 * Dq * B)
    v1 = 2 * Dq - 7.5 * B + delta
    v2 = 12 * Dq - 7.5 * B + delta
    v3 = 2 * delta
    return v1, v2, v3

def objective(params):
    Dq, B = params
    if Dq <= 0 or B <= 0: return 1e10
    v1, v2, v3 = get_energies(params)
    return (v1 - 8620)**2 + (v2 - 18410)**2 + (v3 - 20250)**2

res = minimize(objective, [1000, 600], method='Nelder-Mead')
print(f"Dq: {res.x[0]:.2f}, B: {res.x[1]:.2f}")
EOF
python3 solution.py
