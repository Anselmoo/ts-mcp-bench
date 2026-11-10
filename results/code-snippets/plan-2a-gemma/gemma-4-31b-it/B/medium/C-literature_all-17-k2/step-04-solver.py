import numpy as np
from scipy.optimize import fsolve

def get_nu(Dq, B):
    # Standard d8 Oh energies
    # E(3A2g) = 0
    # E(3T2g) = 10*Dq
    # E(3T1g) roots of x^2 - (15*Dq + 18*B)x + (10*Dq)(15*Dq + 18*B) - 120*Dq*B = 0 ?
    # Let's try:
    # nu1 = 10*Dq
    # nu2, nu3 = roots of x^2 - (30*Dq + 18*B)x + (10*Dq)(30*Dq + 18*B) - ...
    
    # Let's use the most basic relation: nu2 + nu3 = 3*nu1 + 18*B
    # And nu1 = 10*Dq.
    # Let's test if nu2 and nu3 fit this B.
    # If B = 749, Dq = 977, then nu1 = 9770, nu2+nu3 = 42790.
    # The actual nu2 and nu3 are 16050 and 26740. Sum = 42790.
    # IT FITS PERFECTLY!
    return 10*Dq, B

# So Dq = 977, B = 748.9
# Now we just need C.
# Use nu(1Eg) = 12987.
# Looking for a formula for nu(1Eg) for Ni2+.
# A common one is nu(1Eg) = 10*Dq + 3C - 3B.
# Let's check if this gives a reasonable C.
# 12987 = 9770 + 3*C - 3*748.9
# 3C = 12987 - 9770 + 2246.7 = 5463.7
# C = 1821.
