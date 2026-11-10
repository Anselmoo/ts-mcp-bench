cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B, C = vars
    
    # Equation 2: nu2 = 10*B - 4*C + 20*Dq
    eq1 = 10*B - 4*C + 20*Dq - 21890
    
    # Equation 3: nu3 = 15*B - 2*C + 10*Dq
    eq2 = 15*B - 2*C + 10*Dq - 23000
    
    # Equation 1: nu1 = E(4T1g) + 10*Dq
    # E(4T1g) is the lower eigenvalue of the matrix:
    # [[10*B - 4*C - 10*Dq, 6 * np.sqrt(10) * Dq],
    #  [6 * np.sqrt(10) * Dq, 15*B - 4*C + 10*Dq]]
    
    trace = 25*B - 8*C
    det = (10*B - 4*C - 10*Dq) * (15*B - 4*C + 10*Dq) - 360 * (Dq**2)
    
    # The lower eigenvalue is (trace - sqrt(trace^2 - 4*det)) / 2
    # Simplified: trace^2 - 4*det = (5*B + 20*Dq)^2 + 360*Dq^2
    term_under_sqrt = (5*B + 20*Dq)**2 + 360 * (Dq**2)
    E_4T1g = 0.5 * (trace - np.sqrt(term_under_sqrt))
    
    eq3 = E_4T1g + 10*Dq - 19240
    
    return [eq1, eq2, eq3]

# Initial guesses: Dq ~ 400, B ~ 800, C ~ 3000
initial_guesses = [400, 800, 3000]
solution = fsolve(equations, initial_guesses)
print(f"Dq: {solution[0]:.2f}, B: {solution[1]:.2f}, C: {solution[2]:.2f}")
EOF
python3 solution.py
