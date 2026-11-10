import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    # nu1 = 10 Dq
    nu1 = 10 * Dq
    
    # nu2, nu3 are roots of:
    # x^2 - (15*Dq + 42*B)*x + (120*Dq**2 + 210*Dq*B + 294*B**2) = 0
    # No, let's use the standard formula:
    # E(^4T1g) = 0.5 * (15*Dq + 30*B) +/- 0.5 * sqrt((15*Dq - 30*B)**2 + 120*Dq*B) 
    # Wait, let's check that again. 
    # For d3, the free ion terms are 4F and 4P. 
    # 4F -> 4A2g, 4T2g, 4T1g
    # 4P -> 4T1g
    # Energies relative to 4A2g:
    # nu1 = 10 Dq
    # The 4T1g states are the roots of x^2 - (15*Dq + 30*B)*x + ...
    # Actually, the roots are:
    # E = 0.5 * (15*Dq + 30*B) +/- 0.5 * sqrt((15*Dq - 30*B)**2 + 120*Dq*B) 
    # No, that's for d2. 
    
    # Let's use the correct d3 formula:
    # nu1 = 10 Dq
    # nu2 = 15 Dq + something
    # The roots for nu2 and nu3 are:
    # x = 0.5 * (15*Dq + 42*B) +/- 0.5 * sqrt((15*Dq - 12*B)**2 + 120*Dq*B)
    # Let's check if this makes sense for B=0: x = 0.5*(15Dq) +/- 0.5*(15Dq) = 15Dq, 0.
    # That's not right. 
    
    # Let's use the most reliable source for d3:
    # nu1 = 10 Dq
    # nu2 = 1.5*nu1 + ... 
    # Energy of 4T1g(F) = 15 Dq + (something)
    # Energy of 4T1g(P) = 15 B + 15 Dq + (something)
    
    # Let's try this one:
    # x = 0.5 * (15*Dq + 30*B) +/- 0.5 * sqrt((15*Dq - 30*B)**2 + 120*Dq*B)
    # Wait, if Dq is large, nu2 -> 15 Dq. 
    # If B=0, nu2 = 15 Dq.
    # Let's check 0.5 * (15*Dq) +/- 0.5 * sqrt((15*Dq)**2) = 15*Dq or 0.
    # 0 is the ground state? No, nu2 should be the first excited 4T1g.
    # For B=0, nu1=10Dq, nu2=15Dq.
    
    # Let's use the formula from a textbook:
    # nu2 = 0.5 * (15*Dq + 30*B) - 0.5 * sqrt((15*Dq - 30*B)**2 + 120*Dq*B)
    # Wait, if B=0, nu2 = 15 Dq - 15 Dq = 0. Still wrong.
    
    # Correct formula for d3 in Oh:
    # nu1 = 10 Dq
    # nu2 = 0.5 * (15*Dq + 30*B) - 0.5 * sqrt(...) ? No.
    # Let's try:
    # E(^4T2) = 10 Dq
    # E(^4T1g(F)) = 0.5 * (15 Dq + 30 B) - 0.5 * sqrt((15 Dq - 30 B)^2 + 120 Dq B) 
    # This is definitely wrong.
    
    # Let's use:
    # E(^4T1g(F)) = 0.5 * (15 Dq + 30 B) + 0.5 * sqrt((15 Dq - 30 B)^2 - 120 Dq B)
    # No.
    
    # Let's go back to the roots of:
    # x^2 - (15*Dq + 30*B)*x + (120*Dq**2 + 210*Dq*B + 294*B**2) = 0? No.
    
    # Let's use the Tanabe-Sugano relation for nu2/nu1.
    # For d3, nu2/nu1 starts at 1.5 (at Dq=0) and increases as Dq/B increases.
    # Wait, if nu2/nu1 = 32500/26600 = 1.22, this is IMPOSSIBLE.
    # Because nu2 is always > 1.5 * nu1 for any B > 0?
    # Let's check: nu1 = 10 Dq, nu2 approx 15 Dq.
    # If B is large, nu2 might move, but nu1 and nu2 are both based on Dq.
    # Let's re-read the prompt: 26,600, 32,500 and 12,820.
    # If nu1 = 12,820, then nu2 = 26,600, nu3 = 32,500.
    # Then nu2/nu1 = 26600/12820 = 2.07. This is possible.
    # And nu^2E = ? The prompt says 26,600, 32,500, 12,820 are assigned to 4T2, 4T1, 2E.
    # If the assignment is "respectively" to the energies as listed:
    # nu(4T2) = 26,600
    # nu(4T1) = 32,500
    # nu(2E) = 12,820
    # This means nu2/nu1 = 1.22. 
    # BUT if the assignment is 4T2, 4T1, 2E and the energies are 12,820, 26,600, 32,500:
    # nu(4T2) = 12,820
    # nu(4T1) = 26,600
    # nu(2E) = 32,500 ? (2E is usually lower)
    # OR
    # nu(4T2) = 12,820
    # nu(4T1) = 26,600
    # nu(4T1_P) = 32,500
    # And 2E is not given? But there are 3 bands.
    # Wait, the bands are 26,600, 32,500, 12,820.
    # Maybe they are:
    # nu1 (4T2) = 12,820
    # nu2 (4T1) = 26,600
    # nu3 (4T1) = 32,500
    # But the assignment says "4T2, 4T1, 2E".
    # If 2E is one of them, it must be 12,820.
    # Then the other two are 4T2 and 4T1.
    # So nu1 (4T2) = 26,600 and nu2 (4T1) = 32,500.
    # This brings us back to nu2/nu1 = 1.22.
    
    # Let's check a reliable source for [Cr(CN)6]3-.
    # 10 Dq for [Cr(CN)6]3- is approx 26,600 cm-1.
    # nu1 = 26,600.
    # nu2 = 32,500?
    # Let's see if nu2/nu1 = 1.22 is possible for d3.
    # In Tanabe-Sugano for d3, as Dq/B -> infinity, nu2/nu1 -> 1.5.
    # As Dq/B -> 0, nu2/nu1 -> 1.5 (since both are 0?).
    # No, actually nu2/nu1 is ALWAYS >= 1.5 for d3.
    # Let's check the T-S diagram.
    # For d3, the 4T2 line is 10 Dq.
    # The 4T1(F) line starts at 0 (at Dq=0) and goes up.
    # Wait, at Dq=0, the ground state is 4F. The 4T2 and 4T1(F) are degenerate.
    # So nu1 = 0, nu2 = 0.
    # But as Dq increases, nu1 = 10 Dq.
    # The energy of 4T1(F) is roughly 15 Dq.
    # So nu2/nu1 approx 1.5.
    # Is it possible for nu2/nu1 to be 1.22? No.
    
    # There must be a mistake in my understanding or the prompt.
    # Let's assume the energies are:
    # nu1 (4T2) = 12,820
    # nu2 (4T1) = 26,600
    # nu3 (4T1) = 32,500
    # But the assignment says "4T2, 4T1, 2E".
    # Maybe "2E" is the 12,820 band?
    # Then nu1 (4T2) = 26,600 and nu2 (4T1) = 32,500.
    # Still nu2/nu1 = 1.22.
    
    # What if the bands are:
    # 12,820 = 4T2 (nu1)
    # 26,600 = 4T1 (nu2)
    # 32,500 = 2E? No, 2E is usually low.
    
    # Let's look at the complex K3[Cr(CN)6] again.
    # Known values for [Cr(CN)6]3-:
    # nu1 (4T2) = 26,600 cm-1
    # nu2 (4T1) = 32,500 cm-1 ??
    # Let me check these values online.
    # [Cr(CN)6]3- has nu1 = 26,600 and nu2 = 32,500?
    # Let's search.
