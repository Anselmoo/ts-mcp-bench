cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    B = vars[0]
    Dq = 922.22
    
    # T1g matrix: [[-3*Dq, 6*B], [6*B, 15*B]]
    a = -3 * Dq
    c = 15 * B
    b = 6 * B
    
    term1 = 0.5 * (a + c)
    term2 = 0.5 * np.sqrt((a - c)**2 + 4 * b**2)
    
    E_T1g_ground = term1 - term2
    E_T1g_excited = term1 + term2
    E_T2g = 0
    
    nu1 = E_T2g - E_T1g_ground
    nu3 = E_T1g_excited - E_T1g_ground
    
    return [nu1 - 15730, nu3 - 32750]

# We only have one variable B now
sol = fsolve(lambda B: equations([B])[0], 1000)
print(f"B: {sol[0]}")

# Check nu3
B = sol[0]
Dq = 922.22
a = -3 * Dq
c = 15 * B
b = 6 * B
term1 = 0.5 * (a + c)
term2 = 0.5 * np.sqrt((a - c)**2 + 4 * b**2)
E_T1g_ground = term1 - term2
E_T1g_excited = term1 + term2
nu3 = E_T1g_excited - E_T1g_ground
print(f"Calculated nu3: {nu3}")
EOF
python3 solution.py
