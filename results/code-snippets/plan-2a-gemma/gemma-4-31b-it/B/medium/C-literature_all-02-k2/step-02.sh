cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2):
    Dq, B = vars
    # Try coupling = sqrt(180)*B
    coupling = np.sqrt(180) * B
    # Matrix for T1 states relative to T1(F) at Dq=0
    # H = [[0, coupling], [coupling, 30*B + 10*Dq]]
    # This assumes T1(F) is 0 and T1(P) is 30B + 10Dq
    # Let's use the eigenvalues
    eigvals = np.linalg.eigvalsh([[0, coupling], [coupling, 30*B + 10*Dq]])
    E_low = eigvals[0]
    E_high = eigvals[1]
    
    # nu1 = E(T2) - E_low
    # nu2 = E_high - E_low
    # E(T2) = 10*Dq
    return [10*Dq - E_low - nu1, E_high - E_low - nu2]

nu1 = 17500
nu2 = 25000
sol = fsolve(equations, [1800, 800], args=(nu1, nu2))
print(f"Dq: {sol[0]}, B: {sol[1]}")
EOF
python3 solver.py
