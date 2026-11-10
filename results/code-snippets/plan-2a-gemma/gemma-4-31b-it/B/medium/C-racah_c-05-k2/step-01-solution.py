import numpy as np
from scipy.optimize import fsolve

def energies(Dq, B):
    # For d3, ground state is 4A2g.
    # v1 = 10Dq
    # v2 and v3 are eigenvalues of the matrix for 4T1g states.
    # The matrix elements for d8 (equivalent to d3) are:
    # H11 = 10Dq + 4B
    # H22 = 15B + 10Dq - B  # wait, the offset is 15B
    # Actually, a better matrix is:
    # E(4T1g(F)) = 10Dq + 4B
    # E(4T1g(P)) = 15B + 10Dq - B
    # Mixing = sqrt(120) * B
    # Wait, let's use the formula:
    # v2 = 0.5 * (10Dq + 15B - sqrt((10Dq-15B)**2 + 120*B**2)) + something?
    # Let's use the most common matrix for d3/d8:
    # H = [[10*Dq + 4*B, np.sqrt(120)*B], [np.sqrt(120)*B, 15*B + 10*Dq - B]]
    # No, that's not right.
    # Let's use the energies relative to 4A2g:
    # v1 = 10*Dq
    # v2 and v3 are eigenvalues of [[10*Dq + 4*B, np.sqrt(120)*B], [np.sqrt(120)*B, 15*B + 10*Dq - B]]
    # Let's check Dq=0:
    # [[4B, 10.95B], [10.95B, 14B]]
    # eigvals: lambda^2 - 18B*lambda + (56-120)B^2 = 0
    # lambda^2 - 18B*lambda - 64B^2 = 0
    # (lambda - 21.1B)(lambda + 3.1B) = 0? No.
    # lambda = (18 +/- sqrt(324 + 256))/2 = (18 +/- 24)/2 = 21B, -3B.
    # This still gives a negative energy for v2.
    # The ground state is 4A2g, but at Dq=0, the 4F term is degenerate.
    # The 4F term contains 4A2g, 4T2g, 4T1g(F).
    # So at Dq=0, v1=0, v2=0.
    # Thus, the matrix for T1g should be such that one eigenvalue is 0 at Dq=0.
    # Let's try: H = [[10*Dq, np.sqrt(120)*B], [np.sqrt(120)*B, 15*B + 10*Dq]]
    # Dq=0: [[0, 10.95B], [10.95B, 15B]]
    # lambda^2 - 15B*lambda - 120B^2 = 0
    # lambda = (15 +/- 26.55)/2 = 20.77B, -5.77B.
    # Still negative.
    # Let's use the CORRECT matrix for d3/d8 T1g:
    # The states are 4T1g(F) and 4T1g(P).
    # Without mixing, their energies relative to 4A2g are:
    # E(4T1g(F)) = 10Dq + some_const * B
    # E(4T1g(P)) = 15B + 10Dq + some_const * B
    # Let's use the formulas from a reliable source:
    # v1 = 10Dq
    # v2 = 0.5 * (10Dq + 15B - sqrt((10Dq - 15B)**2 + 120*B**2))
    # v3 = 0.5 * (10Dq + 15B + sqrt((10Dq - 15B)**2 + 120*B**2))
    # WAIT, if Dq=0, v2 = 0.5 * (15B - sqrt(225B^2 + 120B^2)) = 0.5 * (15 - 18.57)B = -1.78B.
    # I keep getting this. Is it possible that v1 is not 10Dq? No, v1 is always 10Dq.
    # Is it possible the formula is:
    # v2 = 0.5 * (10Dq + 15B - sqrt((10Dq - 15B)**2 + 120*B**2)) + 1.5B?
    # Let's check Dq=0: v2 = -1.78B + 1.5B = -0.28B.
    # What if v2 = 0.5 * (10Dq + 15B - sqrt((10Dq - 15B)**2 + 120*B**2)) + 2B?
    # Let's look at the 4F barycenter again.
    # E(4A2g) = -1.5B, E(4T2g) = 10Dq - 1.5B, E(4T1g(F)) = -1.5B (at Dq=0).
    # So v1 = 10Dq, and v2 = E(4T1g(F)) - E(4A2g).
    # At Dq=0, v2 should be 0.
    # The energy of the 4T1g states relative to the barycenter is:
    # E = 0.5 * (10Dq + 15B +/- sqrt((10Dq-15B)**2 + 120*B**2))
    # At Dq=0, E = 0.5 * (15B +/- 18.57B) = 16.78B, -1.78B.
    # So E(4T1g(F)) = -1.78B at Dq=0.
    # But E(4A2g) = -1.5B at Dq=0.
    # So v2 = -1.78B - (-1.5B) = -0.28B.
    # This means 4T1g(F) is the ground state at Dq=0?
    # No, 4A2g, 4T2g, and 4T1g(F) are all part of 4F, so they should be degenerate at Dq=0.
    # The only way they are degenerate is if the 120B^2 term is different.
    # Let's use the formula from "Spectroscopic Properties of Transition Metal Complexes":
    # v1 = 10Dq
    # v2 = 10Dq + 4B - 0.5*sqrt((10Dq-15B)**2 + 120*B**2) --- no.
    # Let's use the most basic relation:
    # v1 = 10Dq
    # v2 = 10Dq + (something)
    # v3 = 15B + v2?
    # Actually, there's a very simple approximation for d3:
    # v1 = 10Dq
    # v2 = 10Dq + 15B - v3
    # v3 = 15B + 10Dq
    # Let's try: v1=17500, v2=23860, v3=37910.
    # 10Dq = 17500
    # v2 + v3 = 23860 + 37910 = 61770
    # 15B + 20Dq = 15B + 35000
    # 15B = 26770 => B = 1784.7
    # Now let's check if this B fits the v2, v3 using a better formula.
    # Let's use v3 - v2 = sqrt((10Dq-15B)**2 + 120*B**2)
    # v3 - v2 = 37910 - 23860 = 14050
    # (10Dq-15B)^2 + 120B^2 = 14050^2 = 197,402,500
    # 10Dq = 17500.
    # (17500 - 15B)^2 + 120B^2 = 197,402,500
    # 306,250,000 - 525,000B + 225B^2 + 120B^2 = 197,402,500
    # 345B^2 - 525,000B + 108,847,500 = 0
    # B = [525,000 +/- sqrt(525,000^2 - 4*345*108,847,500)] / (2*345)
    # B = [525,000 +/- sqrt(275,625,000,000 - 150,207,550,000)] / 690
    # B = [525,000 +/- sqrt(125,417,450,000)] / 690
    # B = [525,000 +/- 354,143] / 690
    # B1 = (525,000 + 354,143) / 690 = 1274
    # B2 = (525,000 - 354,143) / 690 = 247
    # Let's check if v2 = 0.5 * (10Dq + 15B - (v3-v2)) + 1.5B?
    # Let's use the Python script to find B precisely.
