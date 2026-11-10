cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    nu1 = 10 * Dq
    # Based on the relation: nu2 + nu3 = 15B + 30Dq and nu3 - nu2 = sqrt((15B-10Dq)^2 + 120Dq^2)
    # These come from E(T1) = 0.5 * (15B + 30Dq +/- sqrt((15B-10Dq)^2 + 120Dq^2))
    term1 = 15 * B + 30 * Dq
    term2 = np.sqrt((15 * B - 10 * Dq)**2 + 120 * Dq**2)
    nu2 = 0.5 * (term1 - term2)
    nu3 = 0.5 * (term1 + term2)
    return np.array([nu1, nu2, nu3])

def objective(params):
    target = np.array([4070, 7030, 16400])
    calc = get_energies(params)
    return np.sum((target - calc)**2)

res = minimize(objective, [400, 800], bounds=[(0, 2000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Calculated: {get_energies(res.x)}")
EOF
python3 solver.py
