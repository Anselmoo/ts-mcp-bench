import numpy as np
from scipy.optimize import minimize

def calculate_energies(Dq, B, C):
    # For d5 high spin octahedral complex
    # Ground state 6A1g energy is 0.
    # The quartet states are derived from 4G, 4P, 4D.
    # 4G splits into 4T1g(G), 4T2g(G), 4Eg(G)
    # 4P becomes 4T1g(P)
    # 4D splits into 4T2g(D), 4Eg(D)
    
    # Simplified energy expressions for 4T2g(G) and 4Eg(G)
    # These do not mix with other states of the same symmetry significantly.
    # Free ion 4G energy relative to 6S is 10*B.
    # The LF splitting of 4G is:
    # E(4Eg(G)) = 10*B + 5*Dq  (approx)
    # E(4T2g(G)) = 10*B + Dq   (approx)
    # E(4T1g(G)) is lower and mixes with 4T1g(P).
    
    # However, let's use the more accurate expressions:
    # For d5, the quartet states from 4G have energies (relative to 6A1g):
    # E(4Eg) = 10*B + 5*Dq
    # E(4T2g) = 10*B + Dq
    # E(4T1g) is the lowest.
    
    # Let's refine the free ion energy. 
    # The energy of 4G relative to 6S is indeed 10B.
    # But the 6A1g ground state is 6S.
    # Let's check if these fit the data.
    
    return np.array([10*B + Dq, 10*B + 5*Dq]) # 4T2, 4E

# Observed values
nu2 = 21890 # 4T2
nu3 = 23000 # 4E
nu1 = 19240 # 4T1

# From nu3 - nu2 = 4*Dq
Dq = (nu3 - nu2) / 4
B = (nu2 - Dq) / 10

print(f"Dq: {Dq}, B: {B}")
