cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2):
    Dq, B = vars
    # Transition energies for d2 Oh
    # E(^3T1g(F)) is the lower root of:
    # x^2 - (10*Dq + 15*B)x + (20*Dq**2 + 24*Dq*B - 2*B**2) = 0 ? 
    # No, let's use the standard formulas from a textbook.
    # For d2:
    # v1 = 10Dq - 3B + ... (mixing)
    # Actually, a common approach is using the ratio v2/v1.
    # v1 = 10Dq - 2.1 B (approx)
    # v2 = 15B + 10Dq (approx)
    
    # Let's use the exact expressions for E(T1) and E(T2).
    # Let x = 10*Dq.
    # E(3T1g(F)) = -1.5 * B - 0.5 * sqrt(x^2 + 12*B*x + 9*B^2)
    # E(3T2g) = x - 1.5 * B
    # E(3T1g(P)) = 1.5 * B + 0.5 * sqrt(x^2 + 12*B*x + 9*B^2) + 15*B ? No.
    
    # Correct energies for d2 Oh:
    # Let epsilon = 10*Dq
    # E(3T1g_F) = -B - 0.5 * sqrt(epsilon**2 + 12*B*epsilon + 9*B**2)
    # E(3T2g) = epsilon - B
    # E(3T1g_P) = 14*B + 0.5 * sqrt(epsilon**2 + 12*B*epsilon + 9*B**2)
    
    # v1 = E(3T2g) - E(3T1g_F) = epsilon + 0.5 * sqrt(epsilon**2 + 12*B*epsilon + 9*B**2)
    # v2 = E(3T1g_P) - E(3T1g_F) = 15*B + sqrt(epsilon**2 + 12*B*epsilon + 9*B**2)
    
    # Check these:
    # As epsilon -> 0: v1 -> 0 + 0.5*(3B) = 1.5B (Wait, that's not 0)
    # As epsilon -> 0: v2 -> 15B + 3B = 18B (Wait, should be 15B)
    # Something is wrong.
    return [0, 0]

EOF
python3 solver.py
