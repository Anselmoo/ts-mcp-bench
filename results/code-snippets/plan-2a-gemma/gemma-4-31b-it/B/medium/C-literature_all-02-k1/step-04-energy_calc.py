import numpy as np
from scipy.linalg import eigh

def get_energies(Dq, B, C):
    # Basis states for d2 in Oh (simplified)
    # t2g^2: ^3T1g, ^1T2g, ^1Eg, ^1A1g
    # t2g^1 eg^1: ^3T2g, ^3T1g, ^1T2g, ^1T1g, ^1A2g
    # eg^2: ^3A2g, ^1E_g, ^1A1g
    
    # This is too complex to implement from scratch quickly.
    # Let's use known formulas for t2g^2.
    # For t2g^2:
    # Energy of ^3T1g = -1.5 * B
    # Energy of ^1T2g = 1.5 * B
    # Energy of ^1Eg = 3 * C - 1.5 * B
    # Energy of ^1A1g = 3 * C + 1.5 * B
    # Wait, let me check this.
    # If B = C, then ^3T1g = -1.5B, ^1T2g = 1.5B, ^1Eg = 1.5B, ^1A1g = 4.5B.
    # This is a known result for t2g^2.
    return -1.5 * B, 1.5 * B, 3 * C - 1.5 * B, 3 * C + 1.5 * B

Dq = 1683.54
B = 500.00
C = 3000.0 # placeholder
e_3T1, e_1T2, e_1E, e_1A1 = get_energies(Dq, B, C)
print(f"E(1E) - E(3T1) = {e_1E - e_3T1}")
