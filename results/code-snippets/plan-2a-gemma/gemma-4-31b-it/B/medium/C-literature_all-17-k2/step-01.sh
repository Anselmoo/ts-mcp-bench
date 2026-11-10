cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def energies(params):
    Dq, B = params
    # For d8, the triplet states are A2g, T2g, T1g(1), T1g(2)
    # Transition energies:
    # nu1 = E(T2g) - E(A2g) = 10 * Dq
    # T1g states are mixed. The matrix for T1g is (in units of B):
    # The states are T1g(F) and T1g(P).
    # In terms of Dq and B:
    # E(A2g) = -12 * Dq + 3 * B # relative to some origin
    # E(T2g) = -2 * Dq + 3 * B
    # For T1g:
    # H = [[ -6*Dq + 3*B, 6*sqrt(2)*Dq ],
    #      [ 6*sqrt(2)*Dq, 15*B - 6*Dq ]]
    # Let's check this matrix.
    # Actually, a better source says:
    # The eigenvalues of T1g are roots of:
    # lambda^2 - (9*Dq + 18*B) lambda + (18*B * 9*Dq - 24*Dq^2) = 0 ?
    # No.
    
    # Let's use the known relation for d8:
    # nu1 = 10*Dq
    # nu2 = (15*Dq + 18*B - sqrt((15*Dq - 18*B)**2 + 120*Dq*B)) / 2
    # nu3 = (15*Dq + 18*B + sqrt((15*Dq - 18*B)**2 + 120*Dq*B)) / 2
    # Wait, let's verify this nu2, nu3 formula.
    # Sum: nu2 + nu3 = 15*Dq + 18*B
    # Product: nu2 * nu3 = ( (15*Dq+18*B)^2 - (15*Dq-18*B)^2 - 120*Dq*B ) / 4
    # = ( 540*Dq*B - 120*Dq*B ) / 4 = 420*Dq*B / 4 = 105*Dq*B.
    
    # Let's test this with some known values. For Ni(H2O)6(2+), 10Dq approx 8500, B approx 600.
    # nu1 = 8500
    # nu2 = (15*850 + 18*600 - sqrt((15*850 - 18*600)**2 + 120*850*600)) / 2
    # = (12750 + 10800 - sqrt((12750 - 10800)**2 + 61200000)) / 2
    # = (23550 - sqrt(1950**2 + 61200000)) / 2
    # = (23550 - sqrt(3802500 + 61200000)) / 2
    # = (23550 - 8062) / 2 = 15488 / 2 = 7744.
    # This nu2 is lower than nu1. That's wrong. nu2 must be > nu1.
    
    return None

# Let's try a different source for d8 energy formulas.
# E(3A2g) = 0
# E(3T2g) = 10*Dq
# E(3T1g) roots of: x^2 - (15*Dq + 18*B)x + (15*Dq+18*B)*10*Dq + something?
# No. Let's use the d2 formulas and shift.
# For d2:
# E(3F) -> T1g, T2g, A2g
# E(3P) -> T1g
# E(3T1g(F)) = -Dq + ...
# E(3T2g) = 10Dq - ...
# Let's use the matrix:
# For d2:
# T1g(F) energy: -Dq
# T1g(P) energy: -Dq + 15B
# Interaction: 6*sqrt(2)*Dq
# Matrix for T1g:
# [[ -Dq, 6*sqrt(2)*Dq ],
#  [ 6*sqrt(2)*Dq, -Dq + 15B ]]
# Let's shift everything so A2g (d8) is 0.
# In d2, A2g is the highest of the 3F states: E(3A2g) = 12Dq
# So for d8:
# E(3A2g) = 0
# E(3T2g) = 4Dq - 12Dq = -8Dq? No.
# Wait, in d2, E(3A2g) = 12Dq, E(3T2g) = 4Dq, E(3T1g(F)) = -Dq (approx).
# So for d8:
# nu1 = E(3T2g) - E(3A2g) = 4Dq - 12Dq = -8Dq. Still negative.
# I must have the d2 energies swapped.
# Let's re-evaluate d2:
# Ground state is 3T1g.
# E(3T1g) approx -Dq
# E(3T2g) = 10Dq (approx)
# E(3A2g) = 12Dq (approx)
# No, for d2: nu1 = 3T1g -> 3T2g, nu2 = 3T1g -> 3A2g.
# For d8: ground state is 3A2g.
# nu1 = 3A2g -> 3T2g = 10Dq. (Given)
# nu2 = 3A2g -> 3T1g(1)
# nu3 = 3A2g -> 3T1g(2)
# The states in d8 are the same as d2.
# E(3A2g) in d2 is 12Dq (relative to 3F origin).
# E(3T2g) in d2 is 4Dq (relative to 3F origin).
# Wait, 4 - 12 = -8. This is not working.
EOF
python3 solver.py
