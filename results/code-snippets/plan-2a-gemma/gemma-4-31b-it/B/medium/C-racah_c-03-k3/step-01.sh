cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    nu1 = 10 * Dq
    # The T1g states are the eigenvalues of the matrix:
    # [15*Dq - B, sqrt(12)*B]
    # [sqrt(12)*B, 15*B]
    # No, let's use the more standard matrix for d3:
    # The transitions are to ^4T2g (10Dq), ^4T1g(F), and ^4T1g(P).
    # The energy of ^4T1g states relative to ^4A2g:
    # These are the roots of X^2 - (30Dq + 15B)X + (225Dq^2 + 150DqB + 36B^2) = 0
    # Wait, let me check that again.
    
    # Let's try a different approach. I will use the values and see which B fits.
    # Nu1 = 19170, Nu2 = 27260, Nu3 = 42610
    return [0, 0]

# Let's instead solve for B and Dq using nu1 = 10Dq and the root formula
nu1 = 19170
nu2 = 27260
nu3 = 42610

Dq = nu1 / 10.0
# Try different B values and check Nu2, Nu3
for B in np.arange(700, 1100, 1):
    # Roots of X^2 - (30*Dq + 15*B)*X + (225*Dq**2 + 150*Dq*B + 36*B**2) = 0
    a = 1
    b = -(30 * Dq + 15 * B)
    c = 225 * Dq**2 + 150 * Dq * B + 36 * B**2
    delta = b**2 - 4*a*c
    if delta >= 0:
        x1 = (-b - np.sqrt(delta)) / (2*a)
        x2 = (-b + np.sqrt(delta)) / (2*a)
        if abs(x1 - nu2) < 100 and abs(x2 - nu3) < 100:
            print(f"Dq: {Dq}, B: {B}, x1: {x1}, x2: {x2}")
EOF
python3 solution.py
