cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    # For d7, replace Dq with -Dq in d3 formulas
    # Note: Dq in d3 is usually positive. For d7, we use Dq > 0 but plug in -Dq.
    dq_d3 = -Dq
    
    e_4a2 = 0
    e_4t2 = 10 * dq_d3
    
    term1 = 0.5 * (15*B + 10*dq_d3)
    term2 = 0.5 * np.sqrt((15*B - 10*dq_d3)**2 + 120*dq_d3**2)
    
    e_4t1_f = term1 - term2
    e_4t1_p = term1 + term2
    
    # Now find the differences relative to the ground state
    # In d7, the ground state is 4T1(F)
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
