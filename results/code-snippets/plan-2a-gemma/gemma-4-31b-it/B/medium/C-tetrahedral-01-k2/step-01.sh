cat << 'EOF' > solve_lf.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    # Transitions for d3 Oh / d7 Td
    # v1 = 10*Dq
    # v2 and v3 are roots of the secular equation for 4T1
    # The energies relative to the ground state 4A2 are the roots of:
    # x^2 - (15*B + 10*Dq)x + 150*B*Dq = 0  -- No, this was wrong.
    
    # Let's use the correct matrix for 4T1:
    # H = [[15*B - 10*Dq, sqrt(120)*Dq],
    #      [sqrt(120)*Dq, 10*Dq]]
    # Wait, these are relative to the ground state 4A2?
    # Let's use the standard T-S formulas:
    # E(4A2) = -12*Dq
    # E(4T2) = -2*Dq
    # E(4T1) roots of x^2 - (15*B - 12*Dq)x - 150*B*Dq = 0? No.
    
    # Let's try another form:
    # v1 = 10*Dq
    # v2 = -10*Dq + 15*B + ...
    
    # The correct secular determinant for 4T1 (relative to 4A2):
    # det | x - (15*B - 10*Dq)  -sqrt(120)*Dq |
    #     | -sqrt(120)*Dq      x - 10*Dq      | = 0
    # (x - (15*B - 10*Dq))(x - 10*Dq) - 120*Dq^2 = 0
    # x^2 - (15*B - 10*Dq + 10*Dq)x + (15*B - 10*Dq)*10*Dq - 120*Dq^2 = 0
    # x^2 - 15*B*x + 150*B*Dq - 100*Dq^2 - 120*Dq^2 = 0
    # x^2 - 15*B*x + 150*B*Dq - 220*Dq^2 = 0
    
    # Let's test this:
    # roots are v2 and v3.
    # v2 + v3 = 15*B
    # v2 * v3 = 150*B*Dq - 220*Dq^2
    
    v1_obs = 4070
    v2_obs = 7030
    v3_obs = 16400
    
    return [10*Dq - v1_obs, 15*B - (v2_obs + v3_obs)]

# This is a very simple system.
# 10*Dq = 4070 => Dq = 407
# 15*B = 23430 => B = 1562
# Now check if v2*v3 = 150*B*Dq - 220*Dq^2
# 7030 * 16400 = 115,292,000
# 150 * 1562 * 407 - 220 * 407^2 = 95,358,300 - 36,437,580 = 58,920,720
# Not matching.
EOF
python3 solve_lf.py
