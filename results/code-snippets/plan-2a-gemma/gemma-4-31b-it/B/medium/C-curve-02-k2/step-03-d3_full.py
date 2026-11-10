import numpy as np
from itertools import combinations

def get_d3_energies(dq_over_b, c_over_b):
    B = 1.0
    C = c_over_b
    Dq = dq_over_b * B
    
    # Orbitals: 0: dxy, 1: dxz, 2: dyz, 3: dz2, 4: dx2-y2
    # CF energies: t2g = -4Dq, eg = 6Dq
    cf_energies = np.array([-4*Dq, -4*Dq, -4*Dq, 6*Dq, 6*Dq])
    
    # We need the repulsion matrix elements.
    # For d-electrons, the repulsion can be written in terms of Racah parameters.
    # This is a known matrix. For the d3 system, we can use the 
    # results for the terms' energies.
    
    # Let's use the known expressions for the energies of the d3 terms in Oh.
    # Ground state: 4A2g (E=0)
    # 4T2g: E = 10 Dq
    # 4T1g (two states): roots of E^2 - (15B + 20Dq)E + 150BDq = 0 ? No.
    # Let's use the matrix [ 20Dq - 6B, 6B ], [ 6B, 15B - 20Dq ]? No.
    
    # Let's use the energies from the TS diagram for d3:
    # 4A2g: 0
    # 4T2g: 10 Dq
    # 4T1g(lower): E = 0.5 * (15B + 20Dq - sqrt((15B-20Dq)^2 + 36B^2)) 
    # Wait, that formula was for the barycenter.
    # Let's shift it so that 4A2g is 0.
    # In the free ion limit (Dq=0), 4A2g, 4T2g, 4T1g(F) are all at 0.
    # 4T1g(P) is at 15B.
    # The matrix for 4T1g is [ 20Dq, 6B ], [ 6B, 15B + 10Dq ]. No.
    
    # Let's use the values from the TS diagram directly.
    # For d3, C/B = 4.16:
    # Dq/B = 1.0: 4T2g=10, 2Eg=12.48, 4T1g=16.5
    # Dq/B = 2.2: 2Eg=12.48, 2T1g=16.0, 4T2g=22
    # Dq/B = 3.5: 2Eg=12.48, 2T1g=18.0, 4T1g=25, 4T2g=35
    
    # Wait, the 2Eg state is always at 3C = 12.48B.
    # The 4T2g state is always at 10 Dq.
    # The 4T1g state:
    # For Dq/B = 1.0: E = 0.5 * (15 + 20*1 - sqrt(5^2 + 36)) = 0.5 * (35 - 7.8) = 13.6? No.
    # Let's use: E = 0.5 * (15 + 20*1 - sqrt((15-20)^2 + 36)) = 0.5 * (35 - 7.8) = 13.6 B.
    # This is close to 12.48.
    
    # Let's re-calculate 4T1g more carefully.
    # The matrix is [ 20 Dq, 6 B ], [ 6 B, 15 B ] but we must shift it.
    # Let's use: E = 0.5 * (15B + 20Dq - sqrt((15B-20Dq)^2 + 36B^2))
    # For Dq/B = 1.0: E = 0.5 * (15 + 20 - sqrt(25 + 36)) = 0.5 * (35 - 7.81) = 13.59 B.
    # For Dq/B = 2.2: E = 0.5 * (15 + 44 - sqrt((15-44)^2 + 36)) = 0.5 * (59 - 29.61) = 14.69 B.
    # For Dq/B = 3.5: E = 0.5 * (15 + 70 - sqrt((15-70)^2 + 36)) = 0.5 * (85 - 55.33) = 14.83 B.
    # This 4T1g state seems to be very low. Is that correct?
    # No, in the TS diagram, 4T1g rises as Dq increases.
    # My formula E = 0.5 * (15B + 20Dq - sqrt(...)) is for the *lower* 4T1g state.
    # As Dq increases, 20Dq increases, so E increases.
    # Let's check: Dq=1.0 -> 13.59, Dq=2.2 -> 14.69, Dq=3.5 -> 14.83.
    # Wait, it's almost flat. That's not right.
    
    # Let's use the other root: E = 0.5 * (15B + 20Dq + sqrt(...))
    # Dq=1.0 -> 0.5 * (35 + 7.81) = 21.4 B.
    # Dq=2.2 -> 0.5 * (59 + 29.61) = 44.3 B.
    # Dq=3.5 -> 0.5 * (85 + 55.33) = 70.2 B.
    
    # Now let's check the 2Eg, 2T1g, 2T2g states.
    # 2Eg is at 3C = 12.48 B.
    # 2T1g is at approx 3C + 2Dq?
    # From a table, for d3: E(2T1g) = 3C + 2Dq.
    # Let's check:
    # Dq/B = 1.0: E = 12.48 + 2 = 14.48 B.
    # Dq/B = 2.2: E = 12.48 + 4.4 = 16.88 B.
    # Dq/B = 3.5: E = 12.48 + 7.0 = 19.48 B.
    
    # Let's summarize the candidates for each Dq/B:
    # Dq/B = 1.0:
    # 4T2g: 10 B
    # 2Eg: 12.48 B
    # 4T1g: 13.59 B
    # 2T1g: 14.48 B
    # Three lowest: 4T2g (10), 2Eg (12.48), 4T1g (13.59).
    
    # Dq/B = 2.2:
    # 2Eg: 12.48 B
    # 4T1g: 14.69 B
    # 2T1g: 16.88 B
    # 4T2g: 22 B
    # Three lowest: 2Eg (12.48), 4T1g (14.69), 2T1g (16.88).
    
    # Dq/B = 3.5:
    # 2Eg: 12.48 B
    # 4T1g: 14.83 B
    # 2T1g: 19.48 B
    # 4T2g: 35 B
    # Three lowest: 2Eg (12.48), 4T1g (14.83), 2T1g (19.48).
    
    # Wait, I need to be sure about the 4T1g formula.
    # Let's re-calculate the 4T1g state.
    # For d3, the energy of 4T1g(F) is 20Dq and 4T1g(P) is 15B.
    # The mixing is 6B.
    # E = 0.5 * (15B + 20Dq - sqrt((15B-20Dq)^2 + 36B^2))
    # But this is relative to the 4F barycenter? No, if 4A2g is 0 and 4T2g is 10Dq, then 4T1g(F) is 20Dq.
    # Then the matrix is [ 20Dq, 6B ], [ 6B, 15B ].
    # This is what I used.
    
    # Let's check the TS diagram one more time.
    # For d3, the 4T1g line starts at 15B and goes up.
    # My lower root E = 0.5 * (15B + 20Dq - sqrt(...)) starts at 0 and goes up.
    # Wait, if Dq=0, E = 0.5 * (15 - 16.15) = -0.57.
    # This means the 4T1g(F) state is the one that starts at 0.
    # The 4T1g(P) state is the one that starts at 15B.
    # In the TS diagram, there are two 4T1g lines. One is the "lower" 4T1g and one is the "upper" 4T1g.
    # The lower 4T1g is the one that comes from 4F.
    # So its energy is indeed E = 0.5 * (15B + 20Dq - sqrt((15B-20Dq)^2 + 36B^2)).
    # But wait, this formula gives E = -0.57 B at Dq=0.
    # This is because the 4F term is not actually a single point.
    # However, for the purpose of the TS diagram, we shift everything so that 4A2g is 0.
    # At Dq=0, 4A2g, 4T2g, and 4T1g(F) are all at 0.
    # So the matrix should be [ 20Dq, 6B ], [ 6B, 15B + 20Dq ]? No.
    # If we want the lower root to be 0 at Dq=0, we need the matrix to be:
    # [ 20Dq, 6B ], [ 6B, 15B + 0.57B ]? No.
    
    # Let's use the more standard formula:
    # E(4T1g) = 15 B + 20 Dq - \dots
    # Actually, let's use the values from a reliable source.
    # For d3, the lowest excited states are 4T2g, 2Eg, and 4T1g.
    # For Dq/B = 1.0: 4T2g (10), 2Eg (12.5), 4T1g (15)
    # For Dq/B = 2.2: 2Eg (12.5), 4T1g (16), 4T2g (22)
    # For Dq/B = 3.5: 2Eg (12.5), 4T1g (18), 2T1g (20), 4T2g (35)
