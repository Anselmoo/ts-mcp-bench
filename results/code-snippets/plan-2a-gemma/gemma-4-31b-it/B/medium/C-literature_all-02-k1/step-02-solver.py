import numpy as np
from scipy.optimize import fsolve

def solve_dq_b(nu1, nu2):
    def eqs(p):
        dq, b = p
        # Transition energies for d2 Oh
        # E(3T1_F) and E(3T1_P) are eigenvalues of:
        # [[-15*b + 10*dq, np.sqrt(120*b*dq + 9*b**2)],
        #  [np.sqrt(120*b*dq + 9*b**2), 15*b + 10*dq]]
        # Wait, these are not the standard matrix elements.
        # Let's use the formula:
        # nu1 = 10*dq - 3*b + correction
        # Let's use the one from a reliable source:
        # E(3T1_F) = -0.5 * (15*b + sqrt(100*dq**2 + 120*b*dq + 9*b**2))
        # E(3T2) = 10*dq - 3*b
        # E(3T1_P) = 0.5 * (15*b + sqrt(100*dq**2 + 120*b*dq + 9*b**2)) + 15*b ? No.
        # Let's use:
        # v1 = 10*dq - 3*b + 0.5 * (sqrt(100*dq**2 + 120*b*dq + 9*b**2) - 15*b) ?
        # Let's try:
        # E(3T1_F) = -3*b - 0.5 * sqrt(100*dq**2 + 120*b*dq + 9*b**2)
        # E(3T2) = 10*dq - 3*b
        # E(3T1_P) = 12*b + 0.5 * sqrt(100*dq**2 + 120*b*dq + 9*b**2)
        
        # Check Dq=0: E(3T1_F) = -3b - 1.5b = -4.5b; E(3T2) = -3b. Diff = 1.5b.
        # Still not 0.
        return [0, 0]

# Actually, let's use the equations:
# nu1 = 10*Dq - 3*B + 0.5*(sqrt(100*Dq**2 + 120*B*Dq + 9*B**2) - 15*B)
# nu2 = 15*B + 10*Dq + 0.5*(sqrt(100*Dq**2 + 120*B*Dq + 9*B**2) - 15*B)
# No, that's not it.

# Let's use the most common ones:
# nu1 = 10*Dq - 3*B + ...
# Actually, for d2:
# nu1 = 10*Dq - 3*B + 0.5 * sqrt( (10*Dq)^2 + 120*B*Dq + 9*B^2 ) - 7.5*B ?
# Let's use the ones from the textbook "Inorganic Chemistry" by Miessler & Tarr or similar.
# For d2:
# E(3T1_F) = -1.5 * B - 0.5 * sqrt( (10*Dq)^2 + 12*B*(10*Dq) + 9*B^2 )
# E(3T2) = 10*Dq - 1.5*B
# E(3T1_P) = 13.5*B + 0.5 * sqrt( (10*Dq)^2 + 12*B*(10*Dq) + 9*B^2 )
# Let's check Dq=0:
# E(3T1_F) = -1.5*B - 1.5*B = -3*B
# E(3T2) = -1.5*B
# Diff = 1.5*B. 
# Wait, is E(3T2) = 10*Dq - 1.5*B correct?
# In d2, the T2 state is just 10*Dq relative to the T1(F) state?
# No.
