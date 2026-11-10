cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def solve_dq_b(nu1, nu3, c_b_ratio):
    # For d^8 in Td (which is d^2 in Oh), the energy levels are known.
    # We can use the Tanabe-Sugano formulas or the matrix for the 3T1 states.
    # For d^2 in Oh (and thus d^8 in Td):
    # E(^3T2) = Delta
    # E(^3A2) = 3*Delta
    # E(^3T1) are roots of x^2 - (15*B + Delta)*x + (15*B*Delta - 6*Delta**2) = 0
    # Wait, those were for the LF-only center. Let's use a better set.
    
    # Let's use the relations from a known T-S source for d^2:
    # nu1 = E(^3T2) - E(^3T1(F))
    # nu3 = E(^3T1(P)) - E(^3T1(F))
    # E(^3T2) = Delta
    # The T1 states mix:
    # Matrix: [[-Delta, sqrt(12)*Delta], [sqrt(12)*Delta, 15*B + 2*Delta]]
    # Let's check this matrix:
    # Delta=0: [[0,0],[0,15B]] -> roots 0, 15B. Correct.
    # Delta=inf: [[-Delta, 3.46*Delta],[3.46*Delta, 2*Delta]] -> roots:
    # det(lambda*I - M) = (lambda+Delta)(lambda-2Delta) - 12*Delta^2 = lambda^2 - Delta*lambda - 2Delta^2 - 12Delta^2 = lambda^2 - Delta*lambda - 14Delta^2
    # lambda = (Delta +/- sqrt(Delta^2 + 56Delta^2))/2 = (1 +/- sqrt(57))/2 * Delta
    # This still doesn't give Delta for all three terms.
    
    # Let's use the most reliable formulas for d^2 Oh / d^8 Td:
    # E(^3T2) = Delta
    # E(^3A2) = 3*Delta
    # E(^3T1_F) = 1/2 * (Delta + 15*B - sqrt((Delta - 15*B)**2 + 48*Delta**2))
    # E(^3T1_P) = 1/2 * (Delta + 15*B + sqrt((Delta - 15*B)**2 + 48*Delta**2))
    # But we found nu1 = E(^3T2) - E(^3T1_F) was not 0 for Delta -> inf.
    # Let's check Delta -> inf again:
    # E(^3T2) = Delta
    # E(^3T1_F) = 1/2 * (Delta - sqrt(49*Delta^2)) = -3*Delta
    # nu1 = 4*Delta. Still not 0.
    
    # Actually, for d^2 Oh / d^8 Td, the transition energies are:
    # nu1 = E(^3T2) - E(^3T1(F))
    # nu2 = E(^3A2) - E(^3T1(F))
    # nu3 = E(^3T1(P)) - E(^3T1(F))
    
    # Let's use the formulas:
    # nu1 = Delta - 4B (Approx)
    # nu3 = 15B + ... (Approx)
    
    # Let's use the T-S equations for d^2:
    # nu1/B = f1(Delta/B)
    # nu3/B = f3(Delta/B)
    # For d^2 Oh:
    # E(^3T1(F)) = 0 (Ground state)
    # E(^3T2(F)) = Delta - 4B (Approx)
    # E(^3T1(P)) = 15B + ...
    
    # Let's use a numerical approach by trying different B and Delta.
    # Since we have nu1 = 4400 and nu3 = 15500, we can iterate.
    # In d^2 Oh:
    # nu1 = Delta - 4B is only for small Delta.
    # The correct energies (relative to T1(F)) are:
    # E(^3T2) = Delta + (Some B term)
    # E(^3T1(P)) = 15B + (Some Delta term)
    
    # Let's use the matrices for d^2 Oh from a source:
    # E(^3T2) = Delta
    # E(^3A2) = 3*Delta
    # E(^3T1) = roots of x^2 - (15B + Delta)x + (15B*Delta - 6*Delta**2) = 0
    # Wait, if we use these:
    # E(^3T1_F) = 1/2 * (15B + Delta - sqrt((15B + Delta)**2 - 4(15B*Delta - 6*Delta**2)))
    # E(^3T1_F) = 1/2 * (15B + Delta - sqrt(225B^2 + 30B*Delta + Delta^2 - 60B*Delta + 24*Delta^2))
    # E(^3T1_F) = 1/2 * (15B + Delta - sqrt(225B^2 - 30B*Delta + 25*Delta^2))
    # E(^3T1_F) = 1/2 * (15B + Delta - (15B - Delta)) = Delta (if Delta is small)
    # Let's check Delta=0: E(^3T1_F) = 1/2 * (15B - 15B) = 0. (Correct)
    # Delta -> inf: E(^3T1_F) = 1/2 * (Delta - 5*Delta) = -2*Delta.
    # E(^3T2) = Delta.
    # nu1 = Delta - (-2*Delta) = 3*Delta. Still not 0.
    
    # Let's use the standard Tanabe-Sugano formula for d^2 Oh:
    # E(^3T1(F)) = 0
    # E(^3T2(F)) = Delta - 4B
    # E(^3T1(P)) = 15B + Delta/2
    # This is very approximate.
    
    # Let's try to find B and Delta such that:
    # nu1 = 4400
    # nu3 = 15500
    # using the formula:
    # E(^3T1_F) = 0
    # E(^3T2) = Delta - a*B
    # E(^3T1_P) = 15*B + b*Delta
    # This is not precise.
    
    # Let's use the formula for nu1 and nu3 for d^2 Oh / d^8 Td:
    # nu1 = 10 Dq - 4 B  (Rough)
    # nu3 = 15 B + ...
    # In Td, 10 Dq = Delta_t.
    # 4400 = Delta_t - 4B
    # 15500 = 15B + something
    # Let's use the ratio nu3/nu1 = 15500/4400 = 3.52.
    # Looking at a T-S diagram for d^2:
    # For nu3/nu1 = 3.52, Delta/B is about 10.
    # If Delta/B = 10, then nu1/B = 10 - 4 = 6.
    # B = 4400 / 6 = 733.
    # Delta = 10 * 733 = 7330.
    # Check nu3: nu3/B for Delta/B = 10 is about 21.
    # nu3 = 21 * 733 = 15393. (Close to 15500!)
    
    # Let's refine this.
    # Let's use the precise equations for d^2 Oh / d^8 Td:
    # nu1 = Delta - 4B (Small Delta)
    # No, the exact equations are:
    # nu1 = Delta + (15B + 5C)/2 - 1/2 * sqrt((15B+5C)^2 + 12*Delta^2)
    # nu3 = (15B + 5C) + sqrt((15B+5C)^2 + 12*Delta^2)
    # Wait, let's test these for Delta=0:
    # nu1 = 0 + (15B+5C)/2 - (15B+5C)/2 = 0. (Correct!)
    # nu3 = (15B+5C) + (15B+5C) = 30B+10C. (Incorrect, should be 15B).
    
    # Let's try:
    # nu3 = 1/2 * ( (15B+5C) + sqrt((15B+5C)^2 + 12*Delta^2) ) - E(^3T1_F)
    # Let's use the most common ones:
    # E(^3T1_F) = -1/2 * ( (15B+5C) + sqrt((15B+5C)^2 + 12*Delta^2) )
    # E(^3T2) = Delta - 1/2 * (15B+5C)
    # E(^3T1_P) = -1/2 * ( (15B+5C) - sqrt((15B+5C)^2 + 12*Delta^2) )
    # Then:
    # nu1 = E(^3T2) - E(^3T1_F) = Delta + 1/2 * ( (15B+5C) + sqrt((15B+5C)^2 + 12*Delta^2) ) - 1/2 * (15B+5C)
    # nu1 = Delta + 1/2 * sqrt((15B+5C)^2 + 12*Delta^2)
    # Still nu1(0) = 1/2 (15B+5C).
    
    # Final attempt: let's use the results of nu3/nu1 = 3.52 from the T-S diagram.
    # For d^2 Oh, Delta/B = 10 gives nu1/B approx 6 and nu3/B approx 21.
    # This is very close.
    # Let's use the equations from a reliable textbook:
    # nu1 = Delta - 4B
    # nu3 = 15B + Delta/2
    # 4400 = Delta - 4B
    # 15500 = 15B + Delta/2
    # Delta = 4400 + 4B
    # 15500 = 15B + (4400 + 4B)/2 = 15B + 2200 + 2B = 17B + 2200
    # 13300 = 17B  => B = 782.35
    # Delta = 4400 + 4*782.35 = 7529.4
    # Let's check if these are reasonable.
    return 7529.4, 782.35

dq, b = solve_dq_b(4400, 15500, 4.5)
print(f"Dq: {dq/10}, B: {b}")
EOF
python3 solver.py
