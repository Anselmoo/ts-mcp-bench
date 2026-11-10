import numpy as np

nu1 = 4400
nu2 = 15500
ratio_C_B = 4.5

# System of equations:
# nu2 = 30*B + np.sqrt((15*B - delta)**2 + 12*B**2)
# nu1 = 0.5*delta - 24*B + 0.5*np.sqrt((15*B - delta)**2 + 12*B**2)

# From nu2: sqrt(...) = nu2 - 30*B
# Substitute into nu1:
# nu1 = 0.5*delta - 24*B + 0.5*(nu2 - 30*B)
# nu1 = 0.5*delta - 24*B + 0.5*nu2 - 15*B
# nu1 = 0.5*delta - 39*B + 0.5*nu2
# 0.5*delta = nu1 - 0.5*nu2 + 39*B
# delta = 2*nu1 - nu2 + 78*B

def solve():
    # Solve for B:
    # (nu2 - 30*B)**2 = (15*B - (2*nu1 - nu2 + 78*B))**2 + 12*B**2
    # (nu2 - 30*B)**2 = (nu2 - 2*nu1 - 63*B)**2 + 12*B**2
    
    # Let a = nu2, b = -30, c = nu2 - 2*nu1, d = -63
    # (a + bB)^2 = (c + dB)^2 + 12B^2
    # a^2 + 2abB + b^2B^2 = c^2 + 2cdB + d^2B^2 + 12B^2
    # (b^2 - d^2 - 12)B^2 + (2ab - 2cd)B + (a^2 - c^2) = 0
    
    a = nu2
    b = -30
    c = nu2 - 2*nu1
    d = -63
    
    coeff_B2 = b**2 - d**2 - 12
    coeff_B = 2*a*b - 2*c*d
    coeff_const = a**2 - c**2
    
    roots = np.roots([coeff_B2, coeff_B, coeff_const])
    for B in roots:
        if B > 0:
            delta = 2*nu1 - nu2 + 78*B
            Dq = delta / 10
            C = ratio_C_B * B
            print(f"B: {B:.2f}, Dq: {Dq:.2f}, C: {C:.2f}, delta: {delta:.2f}")
            # Verify
            sqrt_term = np.sqrt((15*B - delta)**2 + 12*B**2)
            v1_calc = 0.5*delta - 24*B + 0.5*sqrt_term
            v2_calc = 30*B + sqrt_term
            print(f"Verify nu1: {v1_calc:.2f}, nu2: {v2_calc:.2f}")

solve()
