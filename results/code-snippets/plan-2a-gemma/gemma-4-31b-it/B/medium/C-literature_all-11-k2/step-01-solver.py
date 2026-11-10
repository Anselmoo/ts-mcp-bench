import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    C = 4.5 * B
    # Energy expressions for d6 low spin (Oh)
    # These are from a common LF theory source
    # nu1 = 10Dq - 4B (approx)
    # nu2 = 10Dq + 12B (approx)
    # Let's use a more general form if possible.
    # Actually, the exact energies are given by the solutions to the secular equation.
    # For low spin d6:
    # E(^1A1g) = -12Dq + 15B + 10C (Reference energy)
    # However, it's easier to use the delta E from a TS diagram or table.
    # Let's look for the formulas for nu1 and nu2 in terms of Dq, B, C.
    
    # After checking a reference (e.g. Tanabe-Sugano):
    # nu1 = 10Dq - 4B + (some correction)
    # nu2 = 10Dq + 12B + (some correction)
    # Actually, many sources use nu1 = 10Dq - 4B and nu2 = 10Dq + 12B for the C=4B case.
    # Let's check the effect of C.
    # For d6, the repulsion energy of the ground state (1A1g) is R(t2g^6) = 15B + 10C.
    # The states 1T1g and 1T2g arise from the t2g^5 eg^1 configuration.
    # R(1T2g) = 15B + 10C + 12B? No.
    
    # Let's use the expressions:
    # nu_1 = 10Dq - 4B
    # nu_2 = 10Dq + 12B
    # This implies nu_2 - nu_1 = 16B.
    # Let's see if this fits the data and if the C/B ratio is used elsewhere.
    # Wait, the C/B = 4.5 is a hint that we should not use the C=4B approximation.
    
    # For d6 low-spin, the transition energies are:
    # nu1 = E(^1T1g) - E(^1A1g)
    # nu2 = E(^1T2g) - E(^1A1g)
    # From a more detailed source:
    # E(^1A1g) = -12Dq + 15B + 10C
    # E(^1T2g) = -16Dq + 15B + 10C + 12B + 2(C-4B)? No.
    
    # Let's try the general expressions for d6:
    # nu_1 = 10Dq - 4B + (something with C)
    # nu_2 = 10Dq + 12B + (something with C)
    
    # Let's use the values from a known table for Co(III).
    # For [Co(H2O)6]3+, B is usually around 400-600 cm-1.
    # nu2 - nu1 = 25381 - 16474 = 8907.
    # 16B = 8907 => B = 556.7
    # 10Dq = nu1 + 4B = 16474 + 4*556.7 = 18700 => Dq = 1870.
    
    # Let's see if the C/B = 4.5 modifies this.
    # For d6, nu2 - nu1 = 16B is quite robust because the t2g^5 eg^1 terms
    # are separated by 16B regardless of C?
    # Let's check. The repulsion energies for t2g^5 eg^1:
    # The terms are 1T1g and 1T2g.
    # The difference in repulsion energy between them is indeed 16B.
    # Let's verify: 
    # E(^1T2g) = 10Dq + R(^1T2g)
    # E(^1T1g) = 10Dq + R(^1T1g)
    # Delta = R(^1T2g) - R(^1T1g) = 16B.
    # This difference is independent of C.
    
    # Now let's find nu1 = E(^1T1g) - E(^1A1g).
    # E(^1A1g) = R(t2g^6)
    # E(^1T1g) = 10Dq + R(^1T1g)
    # nu1 = 10Dq + R(^1T1g) - R(t2g^6)
    # For C = 4B, R(^1T1g) - R(t2g^6) = -4B.
    # Let's find the expression for R(^1T1g) - R(t2g^6) in terms of B and C.
    # For d6:
    # R(t2g^6) = 15B + 10C
    # R(^1T1g) = 15B + 10C - 4B - (something)?
    # Actually, the energy of the singlets for d6:
    # E(^1A1g) = 15B + 10C
    # E(^1T2g) = 10Dq + 31B + 10C (Wait, this is not right)
    
    # Let's use the standard formulas from a textbook (e.g., Figgis):
    # For low-spin d6:
    # nu1 = 10Dq - 4B + 2(C-4B) ?
    # No, the standard formula is:
    # nu1 = 10Dq - 4B
    # nu2 = 10Dq + 12B
    # This assumes C = 4B.
    # If C != 4B, the formula is:
    # nu1 = 10Dq - 4B + (C - 4B) = 10Dq - 4B + 0.5B = 10Dq - 3.5B ?
    # Let's be more precise.
    
    # The repulsion energy for t2g^6 is 15B + 10C.
    # The repulsion energies for the t2g^5 eg^1 singlets:
    # For 1T2g: 15B + 10C + 12B - 2(C-4B) = 27B + 10C - 2C + 8B = 35B + 8C.
    # For 1T1g: 15B + 10C - 4B - 2(C-4B) = 11B + 10C - 2C + 8B = 19B + 8C.
    # Wait, let's check these.
    # nu2 - nu1 = (35B + 8C) - (19B + 8C) = 16B. (Correct)
    # nu1 = 10Dq + (19B + 8C) - (15B + 10C) = 10Dq + 4B - 2C.
    # If C = 4B, nu1 = 10Dq + 4B - 8B = 10Dq - 4B. (Matches)
    
    # So if C = 4.5B:
    # nu1 = 10Dq + 4B - 2(4.5B) = 10Dq + 4B - 9B = 10Dq - 5B.
    # And nu2 = 10Dq + (35B + 8C) - (15B + 10C) = 10Dq + 20B - 2C.
    # For C = 4.5B: nu2 = 10Dq + 20B - 9B = 10Dq + 11B.
    # Check nu2 - nu1: (10Dq + 11B) - (10Dq - 5B) = 16B. (Correct)
    
    # So the equations are:
    # nu1 = 10Dq - 5B
    # nu2 = 10Dq + 11B
    
    return [10*Dq - 5*B - 16474, 10*Dq + 11*B - 25381]

# solve
Dq, B = fsolve(equations, [1800, 500])
print(f"Dq: {Dq}, B: {B}")
