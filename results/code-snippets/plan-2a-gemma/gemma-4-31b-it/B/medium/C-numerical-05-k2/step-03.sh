cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import least_squares

def calculate_energies(p):
    Dq, B = p
    Delta_o = 10 * Dq
    E_T2g = 0.6 * Delta_o
    E_A2g = 2.0 * Delta_o
    H = np.array([[-0.4 * Delta_o, 6 * B],
                  [6 * B, 15 * B]])
    eigenvalues = np.linalg.eigvals(H)
    E_T1_low = min(eigenvalues).real
    E_T1_high = max(eigenvalues).real
    return np.array([E_T2g - E_T1_low, E_T1_high - E_T1_low, E_A2g - E_T1_low])

def residuals(p):
    # Target values: 15730, 24030, 32750
    return calculate_energies(p) - np.array([15730, 24030, 32750])

res = least_squares(residuals, [1200, 1000])
Dq, B = res.x
print(f"Dq: {Dq}, B: {B}")
print(f"Energies: {calculate_energies(res.x)}")
EOF
python3 solution.py
