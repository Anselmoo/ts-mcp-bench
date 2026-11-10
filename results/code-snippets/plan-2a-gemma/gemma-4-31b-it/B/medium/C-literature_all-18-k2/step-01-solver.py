import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    C = 4.5 * B
    
    # Energies relative to the ground state 3A2g
    # For d8 Oh:
    # v1 = 10 Dq
    # The 3T1g states are eigenvalues of the matrix:
    # H = [[6*Dq, 6*sqrt(10)*Dq], [6*sqrt(10)*Dq, 15*B]] relative to 3A2g?
    # No, that's for C=0.
    # Let's use the form:
    # v1 = 10*Dq
    # v2 = 15*Dq + B - 0.5 * sqrt((15*Dq - B)**2 + 12*B*C) ? No.
    
    # Let's use a more general form for the energies of the 3T1 states
    # The roots of x^2 - (15*Dq + 15*B)x + (15*Dq * 15*B) = 0 is for C=0
    # With C, the matrix for T1 states relative to 3A2g is:
    # [ (15*Dq - 9*B), 6*sqrt(10)*Dq ]
    # [ 6*sqrt(10)*Dq, 15*B - 15*C ] ? No.
    
    # Let's use:
    # v1 = 10 * Dq
    # v2 = 15*Dq + B - sqrt((15*Dq - B)**2 + 12*B*C)/2
    # v3 = 15*Dq + B + sqrt((15*Dq - B)**2 + 12*B*C)/2
    # Wait, that's the same as v2+v3 = 30*Dq + 2*B.
    
    # Let's use the equations for d8 Oh from a reliable source:
    # v1 = 10 Dq
    # v2 = 15 Dq + B - 0.5 * sqrt((15 Dq - B)**2 + 12 B C)
    # v3 = 15 Dq + B + 0.5 * sqrt((15 Dq - B)**2 + 12 B C)
    # This gives v2 + v3 = 30 Dq + 2 B.
    # Let's check v1 = 10600, v2 = 17500, v3 = 27600
    # 17500 + 27600 = 45100
    # 3 * 10600 + 2*B = 31800 + 2*B => 2*B = 13300 => B = 6650 (too high)
    
    # Let's try the other common set:
    # v1 = 10 Dq
    # v2 + v3 = 15 Dq + 15 B
    # v3 - v2 = sqrt((15 Dq - B)**2 + 12 B C) ? No.
    
    return [0, 0]

