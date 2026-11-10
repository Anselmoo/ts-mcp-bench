cat << 'EOF' > solve.py
import numpy as np
from scipy.optimize import minimize

def energies(params):
    Dq, B = params
    if Dq < 0 or B < 0:
        return 1e10
    
    # T1 energies
    # Matrix: [[-4*Dq, 4*np.sqrt(10)*Dq], [4*np.sqrt(10)*Dq, 6*Dq + 15*B]]
    a = -4 * Dq
    b = 4 * np.sqrt(10) * Dq
    c = 6 * Dq + 15 * B
    
    # Eigenvalues of [[a, b], [b, c]]
    # det(xI - M) = (x-a)(x-c) - b^2 = x^2 - (a+c)x + ac - b^2 = 0
    trace = a + c
    det = a * c - b**2
    
    # x = (trace +/- sqrt(trace^2 - 4*det)) / 2
    delta = np.sqrt(max(0, trace**2 - 4*det))
    E1 = (trace - delta) / 2
    E3 = (trace + delta) / 2
    
    E2 = -2 * Dq  # T2g
    E_A2 = 6 * Dq # A2g
    
    v1 = E2 - E1
    v2 = E_A2 - E1
    v3 = E3 - E1
    
    return np.array([v1, v2, v3])

def objective(params):
    target = np.array([8100, 19400, 21600])
    current = energies(params)
    return np.sum((current - target)**2)

from scipy.optimize import differential_evolution
result = differential_evolution(objective, [(0, 5000), (0, 5000)])
print(f"Dq: {result.x[0]}, B: {result.x[1]}")
print(f"Energies: {energies(result.x)}")
EOF
python3 solve.py
