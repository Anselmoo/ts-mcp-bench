cat << 'EOF' > solve.py
import numpy as np
from scipy.optimize import differential_evolution

def get_energies(Dq, B):
    a = -4 * Dq
    c = 15 * B + 6 * Dq
    b = 4 * np.sqrt(10) * Dq
    trace = a + c
    det = a*c - b**2
    delta = np.sqrt(max(0, trace**2 - 4*det))
    E_lower = (trace - delta) / 2
    E_4T2 = -2 * Dq
    E_4A2 = 6 * Dq
    return E_lower, E_4T2, E_4A2

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0: return 1e12
    E_lower, E_4T2, E_4A2 = get_energies(Dq, B)
    nu1 = E_4T2 - E_lower
    nu2 = E_4A2 - E_lower
    return (nu1 - 8100)**2 + (nu2 - 19400)**2

result = differential_evolution(objective, [(0, 2000), (0, 2000)])
Dq, B = result.x
E_lower, E_4T2, E_4A2 = get_energies(Dq, B)
print(f"Dq: {Dq}, B: {B}")
print(f"nu1: {E_4T2 - E_lower}, nu2: {E_4A2 - E_lower}")
EOF
python3 solve.py
