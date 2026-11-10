import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2, nu3, order):
    Dq, B = vars
    # T1g eigenvalues
    # x = [ (15B - 4Dq) +/- sqrt( (15B-4Dq)^2 - 4(15B^2 - 180BDq + 16Dq^2) ) ] / 2
    # Let's check the energy levels from a more reliable source.
    # Actually, the energies of d2 Octahedral are:
    # E(3T2g) = -3Dq
    # E(3A2g) = 12Dq
    # E(3T1g) roots of x^2 - (15B - 4Dq)x + (15B^2 - 180BDq + 16Dq^2) = 0
    # No, that's not right.
    
    # Let's use the general formula for d2:
    # E(T2g) = -3Dq
    # E(A2g) = 12Dq
    # E(T1g) = [ (15B - 4Dq) +/- sqrt( (15B - 4Dq)^2 - 4(15B^2 - 180BDq + 16Dq^2) ) ] / 2
    # No, that's from a different source.
    
    # Let's use the most common form:
    # The matrix for T1g states:
    # [[-4Dq, 6B], [6B, 15B-4Dq]]  <-- this is for d1? No.
    # Let's try [[-4Dq, sqrt(480)*B], [sqrt(480)*B, 15B-4Dq]]
    
    # Actually, let's use the formula from "Inorganic Chemistry" (Miessler & Tarr):
    # For d2, the bands are:
    # v1 = 8Dq
    # v2 = 15B + 8Dq (roughly)
    # v3 = 15B + 18Dq (roughly)
    # This is for large Dq/B.
    
    # Let's use the formula for d2 from a more precise source:
    # E(3T2g) = -3Dq
    # E(3A2g) = 12Dq
    # E(3T1g) = 1/2 * [ (15B - 4Dq) +/- sqrt( (15B - 4Dq)^2 - 4(15B^2 - 180BDq + 16Dq^2) ) ]
    # Wait, the term 15B^2 - 180BDq + 16Dq^2 comes from the determinant.
    
    # Let's try the formula:
    # x^2 - (15B - 4Dq)x + (15B^2 - 180BDq + 16Dq^2) = 0
    # Root x1 (ground state), x2 (excited state)
    
    # Since we have 3 equations and 2 unknowns, we can use the first two and check the third.
    pass

# Instead of fsolve, let's just loop through Dq and B values and find the best fit.
import itertools

nu = [15730, 24030, 32750]
best_fit = None
min_error = float('inf')

for Dq in np.linspace(500, 2000, 500):
    for B in np.linspace(400, 1200, 500):
        # Try Order 0: nu1=T2g-T1g, nu2=T1gP-T1g, nu3=A2g-T1g
        # x^2 - (15B - 4Dq)x + (15B^2 - 180BDq + 16Dq^2) = 0
        # x = [ (15B - 4Dq) - sqrt( (15B-4Dq)^2 - 4(15B^2 - 180BDq + 16Dq^2) ) ] / 2
        # But the determinant is usually: det = (E_T1g_F)(E_T1g_P) - (H12)^2
        # E_T1g_F = -4Dq
        # E_T1g_P = 15B - 4Dq
        # H12 = 6*B (this is for d1? no)
        # Let's use the matrix [[-4Dq, 6B*sqrt(10)], [6B*sqrt(10), 15B-4Dq]]
        # det = (-4Dq)(15B-4Dq) - 360B^2 = -60BDq + 16Dq^2 - 360B^2
        # roots = [ (15B - 8Dq) +/- sqrt( (15B-8Dq)^2 - 4(-60BDq + 16Dq^2 - 360B^2) ) ] / 2
        # discriminant = 225B^2 - 240BDq + 64Dq^2 + 240BDq - 64Dq^2 + 1440B^2 = 1665B^2
        # x1 = (15B - 8Dq - sqrt(1665)*B) / 2
        # x2 = (15B - 8Dq + sqrt(1665)*B) / 2
        
        # Let's try H12 = 6B.
        # det = -60BDq + 16Dq^2 - 36B^2
        # discriminant = (15B-8Dq)^2 - 4(-60BDq + 16Dq^2 - 36B^2) = 225B^2 - 240BDq + 64Dq^2 + 240BDq - 64Dq^2 + 144B^2 = 369B^2
        # x1 = (15B - 8Dq - sqrt(369)*B) / 2
        # x2 = (15B - 8Dq + sqrt(369)*B) / 2
        
        # Try H12 = sqrt(480)*B
        # discriminant = 2145B^2
        # x1 = (15B - 8Dq - sqrt(2145)*B) / 2
        # x2 = (15B - 8Dq + sqrt(2145)*B) / 2
        
        # Let's check v1 = -3Dq - x1, v3 = 12Dq - x1, v2 = x2 - x1
        # This implies v3 - v1 = 15Dq.
        # 32750 - 15730 = 17020 => Dq = 1134.67.
        # v2 = sqrt(disc)*B => B = 24030 / sqrt(disc).
        # then check v1 = -3Dq - (15B - 8Dq - sqrt(disc)*B)/2 = Dq + (sqrt(disc)-15)B/2.
        
        # Let's solve for sqrt(disc) using Dq = 1134.67, v1 = 15730, B = 24030/sqrt(disc)
        # 15730 = 1134.67 + (sqrt(disc)-15)/2 * (24030 / sqrt(disc))
        # 14595.33 = 12015 * (1 - 15/sqrt(disc))
        # 1.2147 = 1 - 15/sqrt(disc)
        # 0.2147 = -15/sqrt(disc)
        # This gives sqrt(disc) negative, impossible.
        
        # This means the transition to T1g(P) must be v3!
        # Let's try: v1 = T2g - T1g, v2 = A2g - T1g, v3 = T1g(P) - T1g
        # v2 - v1 = 15Dq => 24030 - 15730 = 8300 => Dq = 553.33
        # v3 = sqrt(disc)*B => B = 32750 / sqrt(disc)
        # v1 = Dq + (sqrt(disc)-15)B/2 = 553.33 + (sqrt(disc)-15)/2 * (32750 / sqrt(disc))
        # 15730 = 553.33 + 16375 * (1 - 15/sqrt(disc))
        # 15176.67 = 16375 * (1 - 15/sqrt(disc))
        # 0.9268 = 1 - 15/sqrt(disc)
        # 15/sqrt(disc) = 0.0732
        # sqrt(disc) = 15 / 0.0732 = 204.9
        # Disc = 204.9^2 = 41984.
        # Since Disc = (something)*B^2, this is possible.
        # B = 32750 / 204.9 = 159.8.
        # This was the B=160 I found earlier.
