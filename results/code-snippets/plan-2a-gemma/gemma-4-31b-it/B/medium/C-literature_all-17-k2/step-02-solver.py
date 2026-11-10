import numpy as np

def calculate_d8_energies(Dq, B, C):
    # ground state 3A2g: E = 0
    # 3T2g: E = 10*Dq
    
    # For 1Eg:
    # The state 1Eg comes from 1D.
    # The energy of 1D relative to 3F is 3B + 3C. (Check this!)
    # In Oh field, 1D splits into 1Eg and 1T2g.
    # E(1Eg) = E(1D) - 1*Dq?
    # E(3A2g) is part of 3F. E(3A2g) = 12*Dq (relative to 3F centroid).
    # Wait, this centroid stuff is confusing.
    
    # Let's use the formula:
    # nu(1Eg) = 10*Dq + 3C - ... 
    # Let's use a better source.
    # For d8, E(1Eg) - E(3A2g) = 10*Dq + 3C - 3B? No.
    
    # According to a reliable source:
    # nu(1Eg) = 10*Dq + 3C
    # Let's check if this makes sense.
    # nu(1Eg) = 12987, 10Dq = 9770.
    # 3C = 12987 - 9770 = 3217.
    # C = 1072.
    # This is a reasonable value for C (usually C is around 4B).
    # Wait, if B = 749, 4B = 2996. 1072 is too small for C.
    # Usually C is 4.5 * B.
    
    # Let's look for the 1Eg formula again.
    # For d8, E(1Eg) = 10*Dq + 3C - 3B? No.
    # E(1Eg) = 10*Dq + 15B + something? No.
    
    # Let's try: E(1Eg) - E(3A2g) = 10Dq + (something)
    # In many Ni2+ complexes, the 1Eg transition is very close to the 3T1g(1) transition.
    # 1Eg is 12987, 3T1g(1) is 16050.
    # This means 1Eg is BELOW 3T1g(1).
    # My previous calculation nu2 = 16050.
    # This is consistent.
    
    pass

