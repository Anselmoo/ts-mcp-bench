import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B, C = vars
    # Transitions for d3 octahedral
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*B + 30*Dq - np.sqrt((15*B - 30*Dq)**2 + 12*B**2))
    # This is for d2. For d3:
    # nu1 = 10*Dq
    # nu2: Mixing of 4T1(F) and 4T1(P)
    # E(4A2g) = -15*B # Incorrect baseline. Let's use relative energies.
    # Let nu1 = 10*Dq.
    # The matrix for 4T1 states (relative to 4A2g):
    # M = [[20*Dq, sqrt(12)*B], [sqrt(12)*B, 15*B + 20*Dq]]
    # The eigenvalues of this matrix are nu2 and nu4.
    
    # Actually, the matrix is often given as:
    # [[20*Dq, sqrt(12)*B], [sqrt(12)*B, 15*B + 20*Dq]]
    # Let's check nu2 = ( (20*Dq + 15*B + 20*Dq) - sqrt((20*Dq - (15*B + 20*Dq))**2 + 12*B**2) ) / 2
    # nu2 = ( 40*Dq + 15*B - sqrt((-15*B)**2 + 12*B**2) ) / 2
    # nu2 = ( 40*Dq + 15*B - sqrt(237*B**2) ) / 2 = 20*Dq + 15*B/2 - 7.7*B
    
    # Let's use the standard Tanabe-Sugano expressions for d3:
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*B + 30*Dq - np.sqrt((15*B - 30*Dq)**2 + 12*B**2)) # No.
    
    # Correct d3 matrix for 4T1 states:
    # H = [[30*Dq, sqrt(12)*B], [sqrt(12)*B, 15*B]]
    # Relative to 4A2g (which is at 0):
    # 4T2 is at 10*Dq.
    # 4T1 is the eigenvalue of [[20*Dq, sqrt(12)*B], [sqrt(12)*B, 15*B + 20*Dq]]?
    # Let's try this:
    # nu1 = 10*Dq
    # det(lambda*I - [[20*Dq, sqrt(12)*B], [sqrt(12)*B, 15*B + 20*Dq]]) = 0
    # (lambda - 20*Dq)(lambda - 15*B - 20*Dq) - 12*B**2 = 0
    # lambda^2 - (40*Dq + 15*B)lambda + 20*Dq(15*B + 20*Dq) - 12*B**2 = 0
    # lambda = [ (40*Dq + 15*B) - sqrt((40*Dq + 15*B)**2 - 4(300*Dq*B + 400*Dq**2 - 12*B**2)) ] / 2
    # lambda = [ (40*Dq + 15*B) - sqrt(1600*Dq**2 + 1200*Dq*B + 225*B**2 - 1200*Dq*B - 1600*Dq**2 + 48*B**2) ] / 2
    # lambda = [ (40*Dq + 15*B) - sqrt(273*B**2) ] / 2
    # This suggests nu2 is independent of Dq except for the 20*Dq term.
    
    # Let's search for "Cr(CN)6 3- 12820 26600 32500".
    # In most papers:
    # nu1 = 26600 (4T2)
    # nu2 = 32500 (4T1)
    # nu3 = 12820 (2E) -- WAIT, this is the assignment in the prompt!
    # But 12820 is WAY too low for 2E if 4T2 is 26600.
    # Usually 2E is between 4T2 and 4T1.
    # Let's check if nu1 = 12820.
    # Then 10*Dq = 12820 => Dq = 1282.
    # Then nu2 = 26600 or 32500.
    # If nu2 = 26600:
    # 26600 = [ (40*1282 + 15*B) - sqrt(273*B**2) ] / 2
    # 53200 = 51280 + 15*B - 16.52*B
    # 1920 = -1.52*B  => B is negative. Impossible.
    
    # Let's re-verify the matrix for d3 4T1.
    # E(4T1(F)) = 30*Dq (relative to 4A2g) is NOT correct.
    # 4F states: 4A2g(0), 4T2g(10Dq), 4T1g(20Dq) ?
    # Let's check: 1*0 + 3*10 + 3*20 = 90. No.
    # Let's use: 4A2g(0), 4T2g(10Dq), 4T1g(something)
    # For d3, the 4F states are:
    # 4A2g: E = -15 B (centroid)
    # 4T2g: E = -15 B + 10 Dq
    # 4T1g: E = -15 B + 20 Dq ?? No.
    # Let's use the formula:
    # nu1 = 10 Dq
    # nu2 = 15 B + 10 Dq - 0.5 * sqrt((15 B - 10 Dq)^2 + 12 B^2) ?? No.
    
    # Let's try the most common formulas for d3:
    # nu1 = 10 Dq
    # nu2 = 0.5 * (15 B + 30 Dq) - 0.5 * sqrt((15 B - 30 Dq)**2 + 12 B**2)
    # Wait, I used this before. Let's check it again.
    # For Dq=0, nu2 = 0.5(15B - 15B) = 0. Correct.
    # For large Dq, nu2 approx 0.5(30 Dq - (30 Dq - 15 B)) = 7.5 B ? No.
    
    # Let's try:
    # nu1 = 10 Dq
    # nu2 = 0.5 * (15 B + 30 Dq + sqrt((15 B - 30 Dq)**2 + 12 B**2))
    # For Dq=0, nu2 = 0.5(15B + 15B) = 15B. Correct! This is the 4P state.
    # The lower one (4T1(F)) is:
    # nu2 = 0.5 * (15 B + 30 Dq - sqrt((15 B - 30 Dq)**2 + 12 B**2))
    # Wait, for d3, the 4T1(F) state's energy is actually 0 at Dq=0.
    # So nu2 = 0.5 * (15 B + 30 Dq - sqrt((15 B - 30 Dq)**2 + 12 B**2))
    # Let's test this with nu1=12820 and nu2=26600.
    # 10*Dq = 12820 => Dq = 1282
    # 26600 = 0.5 * (15*B + 30*1282 - sqrt((15*B - 30*1282)**2 + 12*B**2))
    # 53200 - 15*B - 38460 = - sqrt((15*B - 38460)**2 + 12*B**2)
    # (14740 - 15*B)^2 = (15*B - 38460)**2 + 12*B**2
    # 14740^2 - 2*14740*15*B + 225*B^2 = 225*B^2 - 2*38460*15*B + 38460^2 + 12*B**2
    # 217267600 - 442200*B = -1153800*B + 1479171600 + 12*B^2
    # 12*B^2 - 711600*B + 1261904000 = 0
    # B^2 - 59300*B + 105158667 = 0
    # B = [ 59300 - sqrt(59300^2 - 4*105158667) ] / 2
    # B = [ 59300 - sqrt(3516490000 - 420634668) ] / 2
    # B = [ 59300 - 55640 ] / 2 = 1830 cm^-1.
    # This B value (1830) is very reasonable for Cr3+.
    
    # Now let's check nu3 = 32500 for 2E.
    # For d3, E(2E) is roughly independent of Dq.
    # E(2E) - E(4A2g) = 0.5 * (15 B - 3 * sqrt( something )) ?
    # The common approximation for 2E in d3 is:
    # nu(2E) = 15 B - 10 Dq ?? No.
    # Let's use: nu(2E) = B + something.
    # Actually, the 2E state is part of the 2H and 2G terms.
    # A better formula: E(2E) = 15 B + 10 Dq - something?
    # Let's use the Python script to find B and C from the given values.
    return 0 # just a placeholder

