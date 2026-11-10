cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import least_squares

def calculate_energies(params):
    Dq, B = params
    Delta = 10 * Dq
    E_T2g = 0.6 * Delta
    E_A2g = 2.0 * Delta
    h_t1g = np.array([[-0.4 * Delta, 6 * B],
                     [6 * B, 15 * B - 0.4 * Delta]])
    e_t1g = np.linalg.eigvalsh(h_t1g)
    E_T1g_low = e_t1g[0]
    E_T1g_high = e_t1g[1]
    return np.array([E_T2g - E_T1g_low, E_T1g_high - E_T1g_low, E_A2g - E_T1g_low])

def residuals(params):
    return calculate_energies(params) - np.array([20700, 30570, 42990])

res = least_squares(residuals, [1600, 1600])
print(f"Dq: {res.x[0]:.2f}, B: {res.x[1]:.2f}")
print(f"Energies: {calculate_energies(res.x)}")
EOF
python3 solver.py
