cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    # For d3, the quartet energies relative to 4A2 are:
    # E(4A2) = 0
    # E(4T2) = 10*Dq
    # E(4T1) = roots of lambda^2 - (15B + 10Dq)lambda + (150*B*Dq + 30*B^2 - 80*Dq^2) = 0
    
    # For d7, we replace Dq with -Dq.
    # E(4A2) = 0
    # E(4T2) = -10*Dq
    # E(4T1) = roots of lambda^2 - (15B - 10Dq)lambda + (-150*B*Dq + 30*B^2 - 80*Dq^2) = 0
    
    # Let's find the roots for E(4T1):
    coeff = [1, -(15*B - 10*Dq), (-150*B*Dq + 30*B**2 - 80*Dq**2)]
    roots = np.roots(coeff)
    e_4t1_f = min(roots)
    e_4t1_p = max(roots)
    e_4t2 = -10 * Dq
    e_4a2 = 0
    
    # In d7, the ground state is 4T1(F).
    # The transitions are:
    v1 = e_4t2 - e_4t1_f
    v2 = e_4t1_p - e_4t1_f
    v3 = e_4a2 - e_4t1_f
    
    return v1, v2, v3

def equations(p):
    Dq, B = p
    v1, v2, v3 = calculate_energies(Dq, B)
    return [v1 - 8100, v2 - 19400]

sol = fsolve(equations, [900, 900])
print(f"Dq: {sol[0]}, B: {sol[1]}")
v1, v2, v3 = calculate_energies(sol[0], sol[1])
print(f"v1: {v1}, v2: {v2}, v3: {v3}")
EOF
python3 solver.py
