cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    # Transition energies for d7 high spin
    # E(^4T1(F)) is ground state.
    # Transition 1: ^4T1(F) -> ^4T2
    # In d3: E(^4T2) - E(^4T1(F)) = 10*Dq - E(^4T1(F))
    # Transition 2: ^4T1(F) -> ^4A2
    # In d3: E(^4A2) - E(^4T1(F)) = 0 - E(^4T1(F)) = -E(^4T1(F))
    # Transition 3: ^4T1(F) -> ^4T1(P)
    # In d3: E(^4T1(P)) - E(^4T1(F))
    
    # Energy of T1 states relative to A2
    term = np.sqrt(237*B**2 - 300*B*Dq + 100*Dq**2)
    ET1F = 0.5 * (15*B + 10*Dq - term)
    ET1P = 0.5 * (15*B + 10*Dq + term)
    
    # For d7, the states are shifted. 
    # The transitions are:
    # nu1 = E(^4T2) - E(^4T1(F))
    # nu2 = E(^4A2) - E(^4T1(F))
    # nu3 = E(^4T1(P)) - E(^4T1(F))
    
    # Let's use the d3 energies relative to A2:
    # E(^4A2) = 0
    # E(^4T2) = 10*Dq
    # E(^4T1F) = ET1F
    # E(^4T1P) = ET1P
    
    # Since T1F is the ground state for d7:
    # nu1 = 10*Dq - ET1F
    # nu2 = 0 - ET1F = -ET1F
    # nu3 = ET1P - ET1F = term
    
    return [
        (10*Dq - ET1F) - 8480,
        (-ET1F) - 16305,
        term - 20360
    ]

# We have 3 equations and 2 variables. Let's use fsolve on two.
from scipy.optimize import least_squares
def fun(vars):
    return equations(vars)

res = least_squares(fun, [800, 800])
print(res.x)
EOF
python3 solution.py
