import numpy as np
from scipy.optimize import fsolve

def transitions(params):
    Dq, B = params
    Delta = 10 * Dq
    
    # For d2 Oh / d8 Td:
    # The states are T1(F), T2(F), A2(F), T1(P)
    # Energies relative to the barycenter of 3F:
    # E(T2) = Delta
    # E(A2) = 2 * Delta
    # The interaction between T1(F) and T1(P)
    # Matrix:
    # [ -Delta, 4 * Delta ]
    # [ 4 * Delta, 15 * B - Delta ]
    # Wait, the interaction term V is often given as 4*Delta in some papers,
    # but let's use the more standard Tanabe-Sugano expressions.
    
    # Actually, let's use the more general matrices from a reliable source:
    # E(T1(F)) and E(T1(P)) are eigenvalues of:
    # [ -Delta, 4 * Delta ]
    # [ 4 * Delta, 15 * B - Delta ]
    # No, the interaction is actually 4*Delta only if we use a specific basis.
    # The correct matrix for d2 Oh (T1 states) is:
    # [ -1.2*Delta + ... ] - this is getting confusing.
    
    # Let's use a different approach.
    # E(T1(F)) = 0.5 * (-Delta - 15*B + np.sqrt((10*B - Delta)**2 + 12*B**2))
    # This formula is common. Let's try it.
    
    E_T1F = 0.5 * (-Delta - 15*B + np.sqrt((10*B - Delta)**2 + 12*B**2))
    E_T2F = 0 # Relative to the barycenter... wait.
    
    # If we use the formula where E(T1F) is the ground state:
    # The T-S diagram tells us:
    # v1 = E(T2) - E(T1)
    # v2 = E(A2) - E(T1)
    # v3 = E(T1P) - E(T1)
    
    # Let's use the matrices from a known source (e.g. a chemistry textbook):
    # E(T1(F)) = 0.5 * (-Delta - 15*B + sqrt((10*B - Delta)**2 + 12*B**2))
    # E(T2(F)) = 0
    # E(A2(F)) = Delta
    # E(T1(P)) = 0.5 * (-Delta + 15*B + sqrt((10*B - Delta)**2 + 12*B**2))
    # This implies v2 - v1 = Delta.
    
    v1 = 0 - E_T1F
    v2 = Delta - E_T1F
    v3 = 0.5 * (-Delta + 15*B + np.sqrt((10*B - Delta)**2 + 12*B**2)) - E_T1F
    
    return [v1 - 3600, v2 - 7870, v3 - 16410]

# This is overdetermined. Let's solve for Dq using v2 - v1 = 10*Dq
Dq_val = (7870 - 3600) / 10
print(f"Dq = {Dq_val}")

# Now solve for B using v1 = 3600
def solve_B(B):
    Delta = 10 * Dq_val
    E_T1F = 0.5 * (-Delta - 15*B + np.sqrt((10*B - Delta)**2 + 12*B**2))
    return (0 - E_T1F) - 3600

from scipy.optimize import fsolve
B_val = fsolve(solve_B, 600)[0]
print(f"B = {B_val}")

# Now check v3
Delta = 10 * Dq_val
E_T1F = 0.5 * (-Delta - 15*B_val + np.sqrt((10*B_val - Delta)**2 + 12*B_val**2))
E_T1P = 0.5 * (-Delta + 15*B_val + np.sqrt((10*B_val - Delta)**2 + 12*B_val**2))
v3_calc = E_T1P - E_T1F
print(f"v3 calculated = {v3_calc}")
