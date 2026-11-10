cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    nu2 = 0.5 * (45 * B - 10 * Dq - np.sqrt((15 * B - 10 * Dq)**2 + 120 * Dq * B))
    nu3 = 0.5 * (45 * B - 10 * Dq + np.sqrt((15 * B - 10 * Dq)**2 + 120 * Dq * B))
    return [nu1 - 17430, nu2 - 25000]

# This didn't work before, let's try nu1 and nu2
sol = fsolve(equations, [1743, 800])
print(sol)
EOF
python3 solver.py
