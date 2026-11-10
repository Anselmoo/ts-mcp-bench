import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    # d8 Octahedral energies relative to 3A2g
    # nu1 = 10 * Dq
    # The two 3T1g states are the eigenvalues of:
    # [ E(3T1g(F))  V ]
    # [ V           E(3T1g(P)) ]
    # Relative to 3A2g:
    # E(3T1g(F)) = -12*Dq + 15*B - (-12*Dq + 3*B) = 12*B ? No.
    # Let's use the correct expressions for d2/d8:
    # Ground state 3A2g: E = -12*Dq + 3*B
    # 3T2g: E = -2*Dq + 3*B  => nu1 = 10*Dq
    # 3T1g: Eigenvalues of [[-12*Dq + 15*B, sqrt(120)*B], [sqrt(120)*B, 0*Dq + 15*B]]
    # Subtracting E(3A2g) = -12*Dq + 3*B:
    # Matrix becomes [[12*B, sqrt(120)*B], [sqrt(120)*B, 12*Dq + 12*B]]
    # This doesn't look right.
    
    # Let's use a different source for d8 energies:
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*Dq + 15*B - sqrt((15*Dq - 15*B)**2 + 120*B**2))
    # nu3 = 0.5 * (15*Dq + 15*B + sqrt((15*Dq - 15*B)**2 + 120*B**2))
    # No, I tried that.
    
    # Let's try the most standard ones:
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*Dq + 15*B - sqrt((15*Dq - 15*B)**2 + 120*B**2)) - This was for d2.
    # For d8, the transition is from 3A2g.
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*Dq + B - sqrt((15*Dq - B)**2 + 120*B**2))
    # No.
    
    # Let's use the values for [NiF6]4- from a known table if possible.
    # Or just use the formula:
    # nu1 = 10 Dq
    # nu2 = 10 Dq + 1.5 B - ...
    # Actually, let's use the formula from a reliable paper:
    # For Ni(II) (d8) in Oh:
    # nu1 = 10 Dq
    # nu2 = 15 B + 0.5(15 Dq - 3 B) - 0.5*sqrt((15 Dq - 3 B)**2 + 120 B**2)
    # nu3 = 15 B + 0.5(15 Dq - 3 B) + 0.5*sqrt((15 Dq - 3 B)**2 + 120 B**2)
    # Let's test this.
    
    # Actually, a simpler one:
    # nu1 = 10 Dq
    # nu3 + nu2 = 15 Dq + 30 B
    # nu3 - nu2 = sqrt((15 Dq - 3 B)**2 + 120 B**2)
    # Let's check nu3 + nu2 = 23840 + 12660 = 36500.
    # 15(740) + 30 B = 11100 + 30 B = 36500 => 30 B = 25400 => B = 846.7.
    # Then nu3 - nu2 = 23840 - 12660 = 11180.
    # sqrt((11100 - 3*846.7)**2 + 120*846.7**2) = sqrt(8560**2 + 86*10^6) = sqrt(73*10^6 + 86*10^6) = 12600.
    # 11180 vs 12600. Close.
    
    return [0, 0]

