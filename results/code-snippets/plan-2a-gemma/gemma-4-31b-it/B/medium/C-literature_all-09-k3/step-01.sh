cat << 'EOF' > solve.py
import numpy as np
from scipy.optimize import fsolve

# Given absorption bands
nu1 = 19720
nu2 = 23260
nu3 = 24980

def equations(vars):
    Dq, B, C = vars
    # High spin d5 energy expressions (relative to 6A1g)
    # Simplified expressions often used for high-spin d5:
    # nu1 (^4T1g) = 10B + 5C - 10Dq
    # nu2 (^4T2g) = 15B + 5C - 10Dq
    # nu3 (^4Eg) = 15B + 5C
    
    # Note: The 4T1g state is actually a result of mixing between 4T1g(G) and 4T1g(P)
    # The energy of 4T1g(G) is -10Dq + 10B + 5C
    # The energy of 4T1g(P) is 15B + 5C (wait, let me check this)
    # For high-spin d5, the 4T1g(P) term energy relative to 6S is 15B + 5C ?
    # No, that's too low.
    # Let's use the simplified expressions first and see if they are consistent.
    
    eq1 = 10*B + 5*C - 10*Dq - nu1
    eq2 = 15*B + 5*C - 10*Dq - nu2
    eq3 = 15*B + 5*C - nu3
    return [eq1, eq2, eq3]

# Initial guesses
guess = [200, 800, 3000]
sol = fsolve(equations, guess)
print(f"Dq: {sol[0]:.2f}, B: {sol[1]:.2f}, C: {sol[2]:.2f}")

EOF
python3 solve.py
