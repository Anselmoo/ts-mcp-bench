import numpy as np
from itertools import combinations, product

def get_d_orbitals_ee():
    # Racah parameters B, C
    # We can use the matrix elements for d-orbitals in terms of B and C.
    # This is quite complex to implement from scratch.
    # Let's use the simplified energy expressions for d4 low spin.
    # From a reliable source:
    # Ground state 3T1g.
    # Transition 1: 3T1g -> 3T2g
    # Transition 2: 3T1g -> 3Eg
    # Transition 3: 3T1g -> 3T1g(F)
    # 
    # For C/B = 4.7, we can find the energies using the TS diagram's numerical values.
    # Let's try to fit the data to nu = a*Dq + b*B
    pass

def fit_data(Dq, B):
    C = 4.7 * B
    # Let's use the expressions for d4 low-spin triplets (approximate)
    # These are derived from the TS diagram for d4.
    # nu1 = 10Dq - 2B
    # nu2 = 10Dq + 2B
    # nu3 = 10Dq + 6B
    # This is just a guess. Let's try to find a better one.
    pass

# Let's try another approach.
# If the transitions are 18850, 19750, 20560.
# The differences are 900 and 810.
# Let's assume nu_i = X + k_i * B.
# nu1 = X + k1*B = 18850
# nu2 = X + k2*B = 19750
# nu3 = X + k3*B = 20560
# then (k2-k1)B = 900 and (k3-k2)B = 810.
# (k2-k1)/(k3-k2) = 900/810 = 10/9 = 1.11
# Let's look for transitions in d4 low-spin where the ratio of differences is ~ 1.11.
# In many TS diagrams, the transitions are something like 10Dq, 10Dq + 2B, 10Dq + 4B.
# But that's a ratio of 1.0.
# What if they are 10Dq - B, 10Dq + B, 10Dq + 3B?
# Ratio (2B)/(2B) = 1.0.
# What if they are 10Dq, 10Dq + 2B, 10Dq + 5B?
# Ratio (2B)/(3B) = 0.66.
# What if they are 10Dq - 2B, 10Dq, 10Dq + 3B?
# Ratio (2B)/(3B) = 0.66.
