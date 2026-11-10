cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    # nu_T2 = 10 * Dq
    # nu_T1F = 0.5 * (15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    # nu_T1P = 0.5 * (15*B + 10*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    nu_T2 = 10 * Dq
    nu_T1F = 0.5 * (15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    nu_T1P = 0.5 * (15*B + 10*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    return np.array([nu_T1F, nu_T2, nu_T1P])

def objective(params):
    target = np.array([4070, 7030, 16400])
    calc = get_energies(params)
    return np.sum((target - calc)**2)

res = minimize(objective, [700, 800], bounds=[(0, 2000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Calculated: {get_energies(res.x)}")
EOF
python3 solver.py
