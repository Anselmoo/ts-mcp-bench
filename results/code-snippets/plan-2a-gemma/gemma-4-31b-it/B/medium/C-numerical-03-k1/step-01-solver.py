import numpy as np
from scipy.optimize import fsolve

def equations(p):
    B, Dq = p
    # Dq is Dq, not 10Dq
    # Energies relative to the barycenter of the 3F term
    # 3F term splits into T1g, T2g, A2g
    # The interaction between T1g(F) and T1g(P) must be included.
    
    # Unperturbed energies relative to barycenter:
    # E(T2g) = 10*Dq - 3*B (wait, let me use a more standard source)
    # E(A2g) = 20*Dq - 3*B
    # E(T1g,F) = -10*Dq - 3*B (approx)
    # E(T1g,P) = 15*B - 3*B = 12*B (approx)
    
    # Let's use the more accurate formulas for d2 (from Tanabe-Sugano or similar):
    # The 3F states:
    # E(T2g) = 10*Dq - 3*B
    # E(A2g) = 20*Dq - 3*B
    # E(T1g,F_unperturbed) = -10*Dq - 3*B
    # The 3P state:
    # E(T1g,P_unperturbed) = 15*B - 3*B = 12*B
    # The interaction between the two T1g states is 6B.
    # But these are barycenters. 
    
    # Let's use the formula for the T1g states from a reliable source:
    # E(T1g) are the roots of:
    # x^2 - (15B - 10Dq)x - (10Dq + 3B)(12B) - (6B)^2 = 0 ? No.
    
    # Let's use the standard energy level expressions for d2 (O_h):
    # E(T2g) = 10*Dq - 3*B
    # E(A2g) = 20*Dq - 3*B
    # E(T1g) = 0.5 * [ (15*B - 10*Dq) - sqrt((15*B + 10*Dq)^2 + 36*B**2) ]
    # This is relative to the barycenter of 3F? No.
    
    # Let's use:
    # nu1 = E(T2g) - E(T1g)
    # nu2 = E(A2g) - E(T1g)
    # nu3 = E(T1g,P) - E(T1g)
    # Where E(T1g,P) is the other root:
    # E(T1g,P) = 0.5 * [ (15*B - 10*Dq) + sqrt((15*B + 10*Dq)^2 + 36*B**2) ]
    
    # Let's re-evaluate E(T2g) and E(A2g).
    # E(T2g) = 10*Dq - 3*B
    # E(A2g) = 20*Dq - 3*B
    # This means nu2 - nu1 = 10*Dq.
    # 24500 - 15490 = 9010 => Dq = 901.
    
    # Now let's use nu1 and nu3 to find B.
    # nu1 = (10*Dq - 3*B) - 0.5 * [ (15*B - 10*Dq) - sqrt((15*B + 10*Dq)**2 + 36*B**2) ]
    # nu3 = 0.5 * [ (15*B - 10*Dq) + sqrt((15*B + 10*Dq)**2 + 36*B**2) ] - 0.5 * [ (15*B - 10*Dq) - sqrt((15*B + 10*Dq)**2 + 36*B**2) ]
    # nu3 = sqrt((15*B + 10*Dq)**2 + 36*B**2)
    
    # Let's test this.
    return [
        (10*Dq - 3*B) - 0.5 * ((15*B - 10*Dq) - np.sqrt((15*B + 10*Dq)**2 + 36*B**2)) - 15490,
        (20*Dq - 3*B) - 0.5 * ((15*B - 10*Dq) - np.sqrt((15*B + 10*Dq)**2 + 36*B**2)) - 24500,
        np.sqrt((15*B + 10*Dq)**2 + 36*B**2) - 0.5 * ((15*B - 10*Dq) - np.sqrt((15*B + 10*Dq)**2 + 36*B**2)) - 32330 # wait this nu3 is wrong.
    ]

# Wait, the nu3 expression:
# nu3 = E(T1g,P) - E(T1g) = sqrt(...)
# No, nu3 = E(T1g,P) - E(T1g) = sqrt((15*B + 10*Dq)**2 + 36*B**2)
# But the E(T1g) in nu1 is the ground state.
# Let's fix the nu3:
# E_ground = 0.5 * [ (15*B - 10*Dq) - sqrt((15*B + 10*Dq)**2 + 36*B**2) ]
# E_T1g_P = 0.5 * [ (15*B - 10*Dq) + sqrt((15*B + 10*Dq)**2 + 36*B**2) ]
# nu3 = E_T1g_P - E_ground = sqrt((15*B + 10*Dq)**2 + 36*B**2)

# Let's use a better set of equations.
