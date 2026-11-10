cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def calculate_energies(p):
    Dq, B = p
    Delta_o = 10 * Dq
    E_T2g = 0.6 * Delta_o
    E_A2g = 2.0 * Delta_o
    H = np.array([[-0.4 * Delta_o, 6 * B],
                  [6 * B, 15 * B]])
    eigvals = np.linalg.eigvals(H)
    E_T1_low = min(eigvals).real
    E_T1_high = max(eigvals).real
    # Assignment B: T2g, A2g, T1g(P)
    return np.array([E_T2g - E_T1_low, E_A2g - E_T1_low, E_T1_high - E_T1_low])

def objective(p):
    target = np.array([15730, 24030, 32750])
    return np.sum((calculate_energies(p) - target)**2)

res = minimize(objective, [600, 1000], method='Nelder-Mead')
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Energies: {calculate_energies(res.x)}")
EOF
python3 solution.py
