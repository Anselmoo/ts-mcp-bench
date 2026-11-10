import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    # For d4, the quintet transition is exactly 10 Dq
    nu_quintet = 10 * Dq
    
    # Triplet states for d4 in Oh field
    # The ^3T1g and ^3T2g states are the lowest triplets.
    # Using the Tanabe-Sugano expressions or similar.
    # For d4, the ^3T1g (F) and ^3T1g (P) states mix.
    # The energies are the eigenvalues of a 2x2 matrix.
    # Matrix elements for ^3T1g states (from a standard source):
    # H11 = 10*Dq - 15*B (relative to ^5E) -- No, this is not correct.
    
    # Let's use the formula for E(^3T1g) from a TS-like calculation.
    # The ground state ^5E has energy -6*Dq + (constant).
    # The ^3T1g state energy is relative to the ^5E ground state.
    # For d4, the ^3T1g state is the lowest triplet.
    # From a table: E(^3T1g) = 10*Dq - 15*B + sqrt((10*Dq-15*B)^2 + 12*B^2) / 2 ... No.
    
    # Let's use the simplified formula for ^3T1g (F) if mixing is small:
    # E(^3T1g,F) = E(^5E) + 10*Dq + (energy of ^3F - ^5D) - something?
    # Actually, let's use the relation:
    # E(^3T1g) = -15 B + 10 Dq + ... (this is also not quite right)
    
    # Let's use a more reliable source for d4 energies.
    # For d4, the ^3T1g(F) state is at approximately 10 Dq - 15 B ? No.
    # The free ion energies: ^5D (0), ^3F (15 B), ^3P (75 B).
    # In an octahedral field, ^3F splits into ^3T1g, ^3T2g, ^3A2g.
    # E(^3T1g,F) = E(^3F) - 4 Dq = 15 B - 4 Dq. (Relative to ^5D free ion)
    # E(^5E) = -6 Dq. (Relative to ^5D free ion)
    # So E(^3T1g,F) - E(^5E) = 15 B - 4 Dq - (-6 Dq) = 15 B + 2 Dq.
    
    # Let's check this. If Dq = 1426, B = 800:
    # E = 15*800 + 2*1426 = 12000 + 2852 = 14852.
    # This is higher than 10 Dq = 14260. Correct.
    # Could 10,970 be E(^3T1g,F) - E(^5E)?
    # 10970 = 15 B + 2 Dq.
    # If 14260 = 10 Dq, then Dq = 1426.
    # 10970 = 15 B + 2*1426 => 15 B = 10970 - 2852 = 8118 => B = 541.
    # This B is a bit low for Cr(II), but possible.
    # But this would mean the triplet is LOWER than the quintet.
    # Let's re-verify: E(^3T1g,F) = 15 B + 2 Dq?
    # Let's re-calculate:
    # ^3F terms in Oh:
    # ^3T1g: -2 Dq + (E_3F)
    # ^3T2g: 1 Dq + (E_3F)
    # ^3A2g: 4 Dq + (E_3F)
    # Ground state ^5E: -6 Dq + (E_5D)
    # E(^3T1g) - E(^5E) = (E_3F - 2 Dq) - (E_5D - 6 Dq) = (E_3F - E_5D) + 4 Dq.
    # E_3F - E_5D = 15 B.
    # So E(^3T1g) - E(^5E) = 15 B + 4 Dq.
    # If Dq = 1426, E = 15*800 + 4*1426 = 12000 + 5704 = 17704.
    # Still higher than 10 Dq.
    
    return nu_quintet
