import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    # Formulas for d3 octahedral
    # nu1 = 10 * Dq
    # nu2 and nu3 are eigenvalues of the T1 matrix
    # The T1 matrix in terms of Dq, B, C:
    # E_F = 15 * Dq
    # E_P = 15 * B + 15 * Dq
    # Interaction = 6 * B (assuming C=4B)
    # However, the prompt says C/B = 4.5.
    # Let's use the interaction term from a more general source.
    # For d3, the matrix is:
    # [ 15*Dq,  6*B ]
    # [ 6*B, 15*B + 15*Dq ]  <-- This is the simplest approximation.
    # But the real one is:
    # E1 = 15*Dq
    # E2 = 15*B + 15*Dq
    # Interaction = sqrt(30 * B^2) ? No.
    
    # Let's use the formula from a textbook:
    # nu1 = 10 * Dq
    # nu2 = 0.5 * (30*Dq + 15*B - sqrt((15*B - 20*Dq)**2 + 120*B**2))
    # nu3 = 0.5 * (30*Dq + 15*B + sqrt((15*B - 20*Dq)**2 + 120*B**2))
    # This is the one I just tested.
    
    # Let's try:
    # nu1 = 10*Dq
    # nu2 = 15*Dq - 1.25*B + 0.5*sqrt((1.25*B - 10*Dq)**2 + 30*B**2) ? No.
    
    # Let's try the most common ones:
    # nu1 = 10 Dq
    # nu2 = 15 Dq + (15 B - 20 Dq)/2 - sqrt((15 B - 20 Dq)^2 + 120 B^2)/2
    # nu3 = 15 Dq + (15 B - 20 Dq)/2 + sqrt((15 B - 20 Dq)^2 + 120 B^2)/2
    
    # Wait, nu1 = 10*Dq = 12300 => Dq = 1230.
    # nu2 = 18500, nu3 = 27900.
    # nu3 - nu2 = sqrt((15*B - 20*Dq)**2 + 120*B**2)
    # (27900 - 18500)**2 = (15*B - 20*1230)**2 + 120*B**2
    # 9400**2 = (15*B - 24600)**2 + 120*B**2
    # 88360000 = 225*B**2 - 738000*B + 605160000 + 120*B**2
    # 345*B**2 - 738000*B + 516800000 = 0
    # B = (738000 +/- sqrt(738000**2 - 4*345*516800000)) / (2*345)
    # B = (738000 +/- sqrt(544644000000 - 713584000000)) / 690
    # This discriminant is negative!
    
    return [0, 0]

