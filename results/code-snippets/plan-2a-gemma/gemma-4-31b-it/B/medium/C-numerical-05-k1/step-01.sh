cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    # Matrix for T1g states
    # [[-3*Dq, 6*B], [6*B, 15*B + 6*Dq]]
    # Eigenvalues of [[a, b], [b, c]] are 0.5 * ((a+c) +/- sqrt((a-c)^2 + 4b^2))
    a = -3 * Dq
    c = 15 * B + 6 * Dq
    b = 6 * B
    
    term1 = 0.5 * (a + c)
    term2 = 0.5 * np.sqrt((a - c)**2 + 4 * b**2)
    
    E_T1g_ground = term1 - term2
    E_T1g_excited = term1 + term2
    E_T2g = -3 * Dq
    E_A2g = 6 * Dq
    
    nu1 = E_T2g - E_T1g_ground
    nu2 = E_A2g - E_T1g_ground
    nu3 = E_T1g_excited - E_T1g_ground
    
    # Observed: 15730, 24030, 32750
    return [nu1 - 15730, nu2 - 24030, nu3 - 32750]

# Since we have 3 equations and 2 variables, we can use the first two
# and then check the third, or use a least-squares fit.
def equations_2(vars):
    Dq, B = vars
    a = -3 * Dq
    c = 15 * B + 6 * Dq
    b = 6 * B
    term1 = 0.5 * (a + c)
    term2 = 0.5 * np.sqrt((a - c)**2 + 4 * b**2)
    E_T1g_ground = term1 - term2
    E_T2g = -3 * Dq
    E_A2g = 6 * Dq
    return [ (E_T2g - E_T1g_ground) - 15730, (E_A2g - E_T1g_ground) - 24030 ]

# Initial guess
Dq_guess, B_guess = 1000, 1000
sol = fsolve(equations_2, [Dq_guess, B_guess])
print(f"Dq: {sol[0]}, B: {sol[1]}")

# Check nu3
Dq, B = sol
a = -3 * Dq
c = 15 * B + 6 * Dq
b = 6 * B
term1 = 0.5 * (a + c)
term2 = 0.5 * np.sqrt((a - c)**2 + 4 * b**2)
E_T1g_ground = term1 - term2
E_T1g_excited = term1 + term2
nu3 = E_T1g_excited - E_T1g_ground
print(f"Calculated nu3: {nu3}")
EOF
python3 solution.py
