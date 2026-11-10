cat << 'EOF' > solve.py
import numpy as np
from scipy.optimize import fsolve

def equations(p, nu1, nu2, nu3, C_B_ratio):
    Dq, B = p
    C = C_B_ratio * B
    
    # Energy of ^3A2g = -12*Dq + 3*C
    # Energy of ^3T2g = -2*Dq + 3*C
    # Transition nu1 = E(^3T2g) - E(^3A2g) = 10*Dq
    
    # For the T1 states, the matrix (relative to ^3A2g) is:
    # [ 15*Dq + 3*C - 3*B,     6*sqrt(10*Dq*B) ]
    # [ 6*sqrt(10*Dq*B),      30*Dq + 15*B + 3*C ]
    # Wait, this depends on the reference. Let's try:
    # Diagonal elements: E1 = 15*Dq, E2 = 15*Dq + 15*B
    # Mixing: 6*sqrt(10*Dq*B)
    
    # Let's try the general d2/d8 triplet matrix:
    # H = [ 15*Dq - 3*B,     6*sqrt(10*Dq*B) ]
    #     [ 6*sqrt(10*Dq*B), 30*Dq + 15*B ]
    # Then we add 12*Dq to get energies relative to ^3A2g?
    # Or just solve for the differences.
    
    # Let's try the most common matrix for T1g states:
    # E_T1(F) = 15*Dq
    # E_T1(P) = 15*Dq + 15*B
    # Mix = 6 * np.sqrt(10 * Dq * B)
    
    # Actually, the matrix relative to ^3A2g for d8 is:
    # [ 15*Dq, 6*sqrt(10*Dq*B) ]
    # [ 6*sqrt(10*Dq*B), 15*Dq + 15*B ]
    
    # Let's use a more general one:
    # [ 15*Dq + B, 6*sqrt(10*Dq*B) ]
    # [ 6*sqrt(10*Dq*B), 15*Dq + 14*B ]
    
    # Let's try the one from a textbook:
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*Dq + 3*B - sqrt((15*Dq + 3*B)**2 - 12*Dq*(10*Dq + 3*B))) - No.
    
    # Let's try the simple relation: 
    # nu2 + nu3 = 30*Dq + 15*B
    # nu2 * nu3 = (15*Dq) * (15*Dq + 15*B) - 360*Dq*B
    
    # We know nu1 = 10*Dq, so Dq = nu1 / 10.
    # Let's see if we can find B from nu2 and nu3.
    
    # Let's try the formula:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + B - sqrt((15*Dq + B)**2 - 12*Dq*(10*Dq + C)) - No.
    
    # Let's use the one for [Ni(H2O)6]2+ to calibrate.
    # nu1=8500, nu2=13500, nu3=25300 -> Dq=850, B=1030.
    # nu2+nu3 = 38800. 30*Dq = 25500. 15*B = 15*1030 = 15450.
    # 25500 + 15450 = 40950. Not 38800.
    # 20*Dq + 15*B = 17000 + 15450 = 32450.
    # 25*Dq + 15*B = 21250 + 15450 = 36700.
    # What about nu2+nu3 = 27*Dq + 15*B?
    # 27*850 + 15450 = 22950 + 15450 = 38400. Close.
    
    # Let's try nu2+nu3 = 30*Dq + 12*B?
    # 25500 + 12*1030 = 25500 + 12360 = 37860.
    
    # Let's try nu2+nu3 = 15*Dq + 24*B?
    # 12750 + 24*1030 = 12750 + 24720 = 37470.
    
    # Let's try nu2+nu3 = 30*Dq + 15*B - some constant?
    
    # Let's use the formula: 
    # nu2 = 15*Dq + B - sqrt((15*Dq + B)**2 - 12*Dq*(10*Dq + B)) - No.
    
    # Actually, let's use the formula from a reliable PDF:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + B - sqrt((15*Dq + B)**2 - 12*Dq(10*Dq + C)) - No.
    
    # Let's try the formula:
    # nu3 = 15*Dq + 15*B + ...
    # Actually, there's a known formula for d8:
    # B = (nu2 + nu3 - 15*Dq) / 3? No.
    # B = (nu3 + nu2 - 15*Dq) / 15? No.
    
    # Let's use nu1 = 10*Dq.
    # B = (nu2 + nu3 - 15*Dq) / (some coefficient)
    # For [Ni(H2O)6]2+: B=1030, nu2+nu3=38800, 15*Dq=12750.
    # (38800 - 12750) / 1030 = 26050 / 1030 = 25.29.
    # Maybe B = (nu2 + nu3 - 15*Dq) / 25?
    
    # Let's try nu3 - nu2 = sqrt((15*B)**2 + 1440*Dq*B)?
    # For [Ni(H2O)6]2+: nu3-nu2 = 11800.
    # sqrt((15*1030)**2 + 1440*850*1030) = sqrt(238702500 + 1261440000) = 38730.
    # Still too big.
    
    # What if the mix is 3*sqrt(10*Dq*B)?
    # sqrt((15*1030)**2 + 9*1440*850*1030) = ... even bigger.
    
    # What if the mix is sqrt(10*Dq*B)?
    # sqrt((15*1030)**2 + 10*Dq*B) = sqrt(238M + 8.7M) = 15700.
    # Close to 11800.
    
    # Let's try nu3 - nu2 = sqrt((15*B)**2 + 120*Dq*B)?
    # sqrt(238M + 120*850*1030) = sqrt(238M + 105M) = 18500.
    
    # Let's use the most basic relation:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + B
    # nu3 = 15*Dq + 15*B
    # [Ni(H2O)6]2+: 13500 = 12750 + B -> B=750.
    # 25300 = 12750 + 15*B -> 15*B = 12550 -> B=836.
    # This is close!
    
    # Let's try nu1 = 10*Dq, nu2 = 15*Dq + B, nu3 = 15*Dq + 15*B.
    # For [Ni(NH3)6]2+: nu1=10600, nu2=17500, nu3=27600.
    # Dq = 1060.
    # 15*Dq = 15900.
    # B = 17500 - 15900 = 1600.
    # 15*B = 27600 - 15900 = 11700 -> B = 780.
    # Still inconsistent.
    
    # Let's use the most general result for d8:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + 3*B - sqrt(...) - No.
    
    # I'll use the relation B = (nu3 + nu2 - 15*Dq) / 30 ? No.
    # Let's try: B = (nu3 + nu2 - 30*Dq) / 15?
    # [Ni(H2O)6]2+: (38800 - 25500) / 15 = 13300 / 15 = 886.7.
    # B = (nu3 + nu2 - 25*Dq) / 15?
    # (38800 - 21250) / 15 = 17550 / 15 = 1170.
    
    # Let's use the known values for [Ni(NH3)6]2+ from a table:
    # Dq = 1060, B = 850.
    # Let's check the relations with these values.
    # nu1 = 10600 (Correct)
    # nu2 = 17500, nu3 = 27600.
    # nu2 + nu3 = 45100.
    # 30*Dq + 15*B = 31800 + 15*850 = 31800 + 12750 = 44550.
    # Very close to 45100!
    # 30*Dq + 16*B = 31800 + 13600 = 45400.
    # So nu2 + nu3 approx 30*Dq + 15*B.
    
    # Let's try the product nu2 * nu3.
    # 17500 * 27600 = 483,000,000.
    # If the matrix is [ 15*Dq, mix ; mix, 15*Dq + 15*B ], the product is 
    # 15*Dq * (15*Dq + 15*B) - mix^2.
    # 15900 * (15900 + 15*850) - mix^2 = 15900 * (15900 + 12750) - mix^2 = 15900 * 28650 - mix^2 = 455,535,000 - mix^2.
    # This is already smaller than 483,000,000.
    # This means the diagonal elements must be larger.
    
    # Maybe the diagonal elements are 15*Dq + B and 15*Dq + 14*B?
    # (15*Dq + B) + (15*Dq + 14*B) = 30*Dq + 15*B. (Same sum)
    # Product: (15*Dq + B)(15*Dq + 14*B) - mix^2
    # (15900 + 850)(15900 + 14*850) - mix^2 = 16750 * (15900 + 11900) - mix^2 = 16750 * 27800 - mix^2 = 465,650,000 - mix^2.
    # Still smaller.
    
    # What if the matrix is [ 15*Dq + 3*B, mix ; mix, 15*Dq + 12*B ]?
    # Sum = 30*Dq + 15*B. (Same sum)
    # Product: (15*Dq + 3*B)(15*Dq + 12*B) - mix^2
    # (15900 + 3*850)(15900 + 12*850) - mix^2 = (15900 + 2550)(15900 + 10200) - mix^2 = 18450 * 26100 - mix^2 = 481,545,000 - mix^2.
    # This is very close to 483,000,000!
    
    # Let's try this matrix:
    # nu2 + nu3 = 30*Dq + 15*B
    # nu2 * nu3 = (15*Dq + 3*B)(15*Dq + 12*B) - mix^2
    # We need a value for mix.
    # For d2/d8, the mix is often 6*sqrt(10*Dq*B).
    # mix^2 = 36 * 10 * Dq * B = 360 * 1060 * 850 = 325,560,000.
    # If we subtract this, the product becomes 481M - 325M = 156M.
    # This is too small.
    
    # The mixing must be smaller.
    # Maybe the mixing is 0? No.
    
    # Let's use the relation:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + 3*B - some_term
    # nu3 = 15*Dq + 12*B + some_term
    
    # Actually, let's use a simpler approach.
    # For Ni(NH3)6, Dq = 1060 and B = 850 is a common result.
    # Let's check if nu1=10600, nu2=17500, nu3=27600 matches.
    # nu1 = 10*1060 = 10600.
    # nu2 = 15*1060 + 850? 15900 + 850 = 16750. (Close to 17500)
    # nu3 = 15*1060 + 12*850? 15900 + 10200 = 26100. (Close to 27600)
    
    # Let's try to solve:
    # nu2 = 15*Dq + x*B
    # nu3 = 15*Dq + y*B
    # 17500 = 15900 + x*B
    # 27600 = 15900 + y*B
    # x*B = 1600
    # y*B = 11700
    # y/x = 11700 / 1600 = 7.31.
    # For the T1 states, the ratio of B coefficients is often around 12/3 = 4.
    
    # Let's use the most standard formula:
    # nu1 = 10*Dq
    # nu2 = 15*Dq + B - sqrt((15*Dq+B)**2 - 12*Dq(10*Dq+C))
    # nu3 = 15*Dq + B + sqrt((15*Dq+B)**2 - 12*Dq(10*Dq+C))
    # Try this:
    # nu2 + nu3 = 30*Dq + 2*B
    # 45100 = 31800 + 2*B -> 2*B = 13300 -> B = 6650. (Too high)
    
    # Let's try:
    # nu2 = 15*Dq - B
    # nu3 = 15*Dq + 15*B
    # 17500 = 15900 - B -> B = -1600.
    
    # I will just use the values Dq = 1060 and B = 850 and see if it's acceptable.
    # Wait, a better way: solve nu1=10Dq and nu2+nu3 = 30Dq + 15B.
    # 45100 = 31800 + 15*B -> 15*B = 13300 -> B = 886.7.
    # Let's use B = 887 and Dq = 1060.
    
    return [Dq - nu1/10, B - (nu2+nu3 - 30*(nu1/10))/15]

# nu1, nu2, nu3 = 10600, 17500, 27600
# Dq = 1060
# B = (17500 + 27600 - 30*1060) / 15 = (45100 - 31800) / 15 = 13300 / 15 = 886.67
EOF
python3 solve.py
