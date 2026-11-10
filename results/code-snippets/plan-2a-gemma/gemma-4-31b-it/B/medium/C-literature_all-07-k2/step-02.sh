cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def calculate_energies(params):
    Dq, B = params
    # E(4Eg) = 10*B
    # E(4T2g) = 10*B - 4*Dq
    # E(4T1g) is the lower eigenvalue of the 2x2 matrix
    Eg_4E = 10 * B
    Eg_4T2 = 10 * B - 4 * Dq
    
    # For 4T1g
    E_G = 10 * B - 10 * Dq
    E_P = 21 * B + 10 * Dq
    V = 6 * Dq
    
    # Eigenvalue: (E_G + E_P - sqrt((E_G - E_P)^2 + 4*V^2)) / 2
    Eg_4T1 = 0.5 * (E_G + E_P - np.sqrt((E_G - E_P)**2 + 4 * V**2))
    
    return np.array([Eg_4T1, Eg_4T2, Eg_4E])

def objective(params):
    observed = np.array([19240, 21890, 23000])
    calculated = calculate_energies(params)
    return np.sum((observed - calculated)**2)

res = minimize(objective, [300, 2000], bounds=[(0, 1000), (0, 5000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
EOF
python3 solution.py
