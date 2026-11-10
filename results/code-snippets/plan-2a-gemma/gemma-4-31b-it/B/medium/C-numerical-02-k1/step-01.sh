cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    # Octahedral d7 High Spin
    # Ground state: 4T1g(F)
    # Transitions: 4T1g(F) -> 4T2g, 4T1g(F) -> 4A2g, 4T1g(F) -> 4T1g(P)
    
    # Energies relative to the barycenter
    # E(4T2g) = -0.5 * 10*Dq + 6*B  (Check: d3 4T2g is 10*Dq above 4A2g)
    # Actually, let's use the d3 energies and then invert.
    # d3 levels relative to 4A2g:
    # 4A2g: 0
    # 4T2g: 10*Dq
    # 4T1g states: roots of secular equation
    
    # Secular equation for T1g states in d3:
    # Matrix:
    # [ 10*Dq + 16*B, -6*B ]
    # [ -6*B, 10*Dq + 16*B + 15*B ]
    # Wait, this is not right.
    
    # Let's use the standard results for d3:
    # E(4T2g) = 10*Dq
    # E(4T1g) roots:
    # lambda^2 - lambda(10*Dq + 31*B) + (10*Dq + 16*B)(10*Dq + 31*B) - (6*B)^2 = 0?
    # No.
    
    # Correct d3 matrix (from textbooks):
    # H = [ 10*Dq + 16*B, -6*B ]
    #     [ -6*B, 10*Dq + 31*B ]
    # Eigenvalues:
    # det(H - lambda I) = (10*Dq + 16*B - lambda)(10*Dq + 31*B - lambda) - 36*B^2 = 0
    # lambda^2 - (20*Dq + 47*B)lambda + (10*Dq + 16*B)(10*Dq + 31*B) - 36*B^2 = 0
    
    # The energies relative to 4A2g (d3) are:
    # nu1_d3 = 10*Dq
    # nu2_d3 = lambda1
    # nu3_d3 = lambda2
    
    # Now for d7 (hole equivalent):
    # The states are the same, just the order is inverted.
    # 4T1g(F) is the ground state.
    # 4T2g is nu1_d7
    # 4A2g is nu2_d7
    # 4T1g(P) is nu3_d7
    
    # Energy relative to 4T1g(F) (d7):
    # nu1_d7 = E(4T2g) - E(4T1g(F)) = 10*Dq - lambda1
    # nu2_d7 = E(4A2g) - E(4T1g(F)) = 0 - lambda1 = -lambda1  -- wait, this can't be right.
    
    # Let's rethink:
    # In d3: E(4A2g) < E(4T2g) < E(4T1g(F)) < E(4T1g(P))
    # In d7: E(4T1g(F)) < E(4T2g) < E(4A2g) < E(4T1g(P))
    # The gaps between these levels are the same because the T1g(F) state is the ground state in d7.
    # So:
    # nu1_d7 = E(4T2g) - E(4T1g(F)) = 10*Dq - (lambda1 - 0) = 10*Dq - lambda1? No.
    
    # Let's use the energies of the states relative to the same barycenter.
    # d3 barycenter is usually set such that 4A2g is 0.
    # E(4A2g) = 0
    # E(4T2g) = 10*Dq
    # E(4T1g,1) = lambda1
    # E(4T1g,2) = lambda2
    
    # For d7, the energies are the negative of the d3 energies relative to a shifted barycenter.
    # E(4T1g,1)_d7 = -lambda1
    # E(4T2g)_d7 = -10*Dq
    # E(4A2g)_d7 = 0
    # E(4T1g,2)_d7 = -lambda2  -- wait, if lambda1 < lambda2, then -lambda2 < -lambda1.
    
    # Let's use:
    # Ground state (d7): 4T1g,1  (which corresponds to 4T1g,2 in d3 but shifted)
    # Let's just use the gaps.
    # Gap 1 (d7): 4T1g(F) -> 4T2g  =  E(4T2g) - E(4T1g(F)) = 10*Dq - lambda1? No.
    # Gap 2 (d7): 4T1g(F) -> 4A2g  =  E(4A2g) - E(4T1g(F)) = 0 - lambda1? No.
    
    # Let's use the property:
    # nu2_d7 - nu1_d7 = E(4A2g) - E(4T2g) = 0 - 10*Dq ? No, 4A2g is above 4T2g in d7.
    # In d3: E(4T2g) - E(4A2g) = 10*Dq.
    # In d7: E(4A2g) - E(4T2g) = 10*Dq.
    # So nu2_d7 - nu1_d7 = 10*Dq.
    # This matches my previous thought.
    
    # Now for nu3_d7:
    # nu3_d7 = E(4T1g,P) - E(4T1g,F)
    # In d3, the T1g states are lambda1 and lambda2.
    # The gap is lambda2 - lambda1.
    # So nu3_d7 = lambda2 - lambda1.
    # Wait, no. nu3_d7 is the transition to the other T1g state.
    # In d7, ground state is the "lower" T1g state.
    # But the "lower" T1g state in d7 corresponds to the "upper" T1g state in d3?
    # Let's check the energies:
    # d3: 4A2g (0) < 4T2g (10Dq) < 4T1g,1 (lambda1) < 4T1g,2 (lambda2)
    # d7: 4T1g,1 (ground) < 4T2g < 4A2g < 4T1g,2
    # Wait, the states in d7 are:
    # 4T1g(F) - this is the one that's lambda1 in d3?
    # No, let's use the Tanabe-Sugano diagram.
    # For d7, the ground state is 4T1g.
    # Transitions are to 4T2g, 4A2g, and 4T1g(P).
    # The transition to 4T1g(P) is the one with the highest energy.
    # So nu3_d7 = E(4T1g,P) - E(4T1g,F).
    # In d3, this is lambda2 - lambda1?
    # No, in d3, 4T1g(F) is lambda1 and 4T1g(P) is lambda2.
    # So nu3_d7 = lambda2 - lambda1.
    # Let's check: in d7, the gap between the two T1g states is the same as in d3.
    # Yes, the mixing is the same.
    # So nu3_d7 = lambda2 - lambda1.
    
    # Let's test this.
    # nu1_d7 = E(4T2g) - E(4T1g,F) = 10*Dq - (lambda1 - 10*Dq)? No.
    # Let's use the relative energies:
    # E(4A2g) = 0
    # E(4T2g) = 10*Dq
    # E(4T1g,1) = lambda1
    # E(4T1g,2) = lambda2
    # For d7:
    # Ground state is 4T1g,1? No, 4T1g,1 is a state.
    # Let's shift the energy so 4T1g,1 is 0.
    # E'(4T1g,1) = 0
    # E'(4T2g) = 10*Dq - lambda1
    # E'(4A2g) = 0 - lambda1
    # This would mean E'(4A2g) < E'(4T2g), which is wrong for d7.
    
    # Correct logic:
    # d7 is the hole-equivalent of d3.
    # To get d7 energies from d3 energies:
    # E_d7 = - E_d3 + constant
    # d3 energies: E(4A2g)=0, E(4T2g)=10Dq, E(4T1g,1)=lambda1, E(4T1g,2)=lambda2
    # d7 energies:
    # E(4A2g)_d7 = -0 = 0
    # E(4T2g)_d7 = -10Dq
    # E(4T1g,1)_d7 = -lambda1
    # E(4T1g,2)_d7 = -lambda2
    # Since lambda2 > lambda1 > 10Dq > 0:
    # -lambda2 < -lambda1 < -10Dq < 0
    # Ground state is 4T1g,2 (which is the 4T1g(F) state in d7).
    # Transitions from 4T1g,2:
    # nu1 = E(4T1g,1)_d7 - E(4T1g,2)_d7 = -lambda1 - (-lambda2) = lambda2 - lambda1
    # nu2 = E(4T2g)_d7 - E(4T1g,2)_d7 = -10Dq - (-lambda2) = lambda2 - 10Dq
    # nu3 = E(4A2g)_d7 - E(4T1g,2)_d7 = 0 - (-lambda2) = lambda2
    # This order is nu1 < nu2 < nu3.
    # Let's check the problem: nu1=9460, nu2=20160, nu3=21160.
    # Our nu3 is the largest, matches.
    # Our nu2 - nu1 = (lambda2 - 10Dq) - (lambda2 - lambda1) = lambda1 - 10Dq.
    # But in our problem nu2 - nu1 = 20160 - 9460 = 10700.
    # So lambda1 - 10Dq = 10700.
    # Also nu3 - nu2 = lambda2 - (lambda2 - 10Dq) = 10Dq.
    # In our problem nu3 - nu2 = 21160 - 20160 = 1000.
    # So 10Dq = 1000 => Dq = 100.
    # This doesn't seem right. 10Dq = 1000 is very small.
    
    # Let's re-examine the transitions for d7:
    # 4T1g(F) -> 4T2g (nu1)
    # 4T1g(F) -> 4A2g (nu2)
    # 4T1g(F) -> 4T1g(P) (nu3)
    # These are the spin-allowed ones.
    # In d3: 4A2g -> 4T2g (nu1), 4A2g -> 4T1g(F) (nu2), 4A2g -> 4T1g(P) (nu3)
    # Hole relation:
    # E(4T1g,F)_d7 = -E(4T1g,P)_d3
    # E(4T2g)_d7 = -E(4T2g)_d3
    # E(4A2g)_d7 = -E(4A2g)_d3
    # E(4T1g,P)_d7 = -E(4T1g,F)_d3
    # Wait, the T1g states swap roles.
    # Let's check:
    # d3: E(4A2g) < E(4T2g) < E(4T1g,F) < E(4T1g,P)
    # d7: E(4T1g,F)_d7 < E(4T2g)_d7 < E(4A2g)_d7 < E(4T1g,P)_d7
    # This is because d7 is the hole equivalent of d3.
    # If we define the energy relative to 4A2g in d3:
    # 4A2g: 0
    # 4T2g: 10Dq
    # 4T1g(F): lambda1
    # 4T1g(P): lambda2
    # Then in d7, the energies relative to some origin are:
    # 4A2g: 0
    # 4T2g: -10Dq
    # 4T1g(F): -lambda2
    # 4T1g(P): -lambda1
    # Now let's find the transitions from 4T1g(F) in d7:
    # nu1 = E(4T2g) - E(4T1g,F) = -10Dq - (-lambda2) = lambda2 - 10Dq
    # nu2 = E(4A2g) - E(4T1g,F) = 0 - (-lambda2) = lambda2
    # nu3 = E(4T1g,P) - E(4T1g,F) = -lambda1 - (-lambda2) = lambda2 - lambda1
    # This order is nu1 < nu2. But nu3 is lambda2 - lambda1.
    # Since lambda1 > 10Dq, lambda2 - lambda1 < lambda2 - 10Dq.
    # So nu3 would be the smallest? That doesn't match nu3 = 21160.
    
    # Let's try another mapping:
    # 4T1g(F) is ground state in d7.
    # Transition nu1: 4T1g(F) -> 4T2g
    # Transition nu2: 4T1g(F) -> 4A2g
    # Transition nu3: 4T1g(F) -> 4T1g(P)
    # These are usually in this order of energy.
    # In d3: 4A2g -> 4T2g (nu1), 4A2g -> 4T1g(F) (nu2), 4A2g -> 4T1g(P) (nu3)
    # The gap E(4A2g) - E(4T2g) is 10Dq in d3.
    # In d7, the gap E(4A2g) - E(4T2g) is also 10Dq.
    # So nu2 - nu1 = E(4A2g) - E(4T2g) = 10Dq.
    # nu2 - nu1 = 20160 - 9460 = 10700.
    # So 10Dq = 10700 => Dq = 1070.
    # Now use nu3. nu3 is the transition to the other T1g state.
    # In d3, the T1g states are lambda1 and lambda2.
    # The difference is lambda2 - lambda1.
    # In d7, the ground state is a T1g state and the third transition is to the other T1g state.
    # So nu3 - nu1 = (E(4T1g,P) - E(4T1g,F)) - (E(4T2g) - E(4T1g,F)) = E(4T1g,P) - E(4T2g).
    # This is getting confusing. Let's just use the d3 formulas and the gap.
    # For d3:
    # nu1 = 10Dq
    # nu2 = lambda1
    # nu3 = lambda2
    # The d7 transitions are:
    # nu1_d7 = lambda1 - 10Dq  (4T1g,F -> 4T2g) -- no
    # Let's use the relation:
    # For d7:
    # nu1 = E(4T2g) - E(4T1g,F)
    # nu2 = E(4A2g) - E(4T1g,F)
    # nu3 = E(4T1g,P) - E(4T1g,F)
    # We know nu2 - nu1 = 10Dq.
    # Also, E(4T1g,F) and E(4T1g,P) are the roots of the same secular equation as in d3.
    # In d3, these roots were lambda1 and lambda2.
    # The difference is lambda2 - lambda1.
    # In d7, this difference is nu3 - (something)?
    # No, the difference between the two T1g states is nu3 - 0 (if ground is 0) = nu3.
    # Wait, if ground is 4T1g,F, then the other T1g state is 4T1g,P.
    # So nu3 = E(4T1g,P) - E(4T1g,F).
    # In d3, this is lambda2 - lambda1.
    # So nu3 = lambda2 - lambda1.
    
    # Let's summarize for d7:
    # 1) 10Dq = nu2 - nu1
    # 2) nu3 = lambda2 - lambda1
    # where lambda1, lambda2 are the roots of:
    # lambda^2 - (20*Dq + 47*B)lambda + (10*Dq + 16*B)(10*Dq + 31*B) - 36*B^2 = 0
    # Wait, these lambda are relative to 4A2g in d3.
    # Let's check if this is consistent.
    # lambda2 - lambda1 = sqrt((20*Dq + 47*B)^2 - 4((10*Dq + 16*B)(10*Dq + 31*B) - 36*B^2))
    # lambda2 - lambda1 = sqrt(400*Dq^2 + 1880*Dq*B + 2209*B^2 - 4(100*Dq^2 + 470*Dq*B + 496*B^2 - 36*B^2))
    # = sqrt(400*Dq^2 + 1880*Dq*B + 2209*B^2 - 400*Dq^2 - 1880*Dq*B - 1840*B^2)
    # = sqrt(369*B^2) = B * sqrt(369) = 19.2 * B.
    # This would mean nu3 = 19.2 * B.
    # But this would mean nu3 doesn't depend on Dq. That's not right.
    
    # Let's use the correct matrix for d3:
    # The T1g states are:
    # E(4T1g,F) = 10Dq + 16B
    # E(4T1g,P) = 10Dq + 31B
    # The mixing is 6B.
    # This is the matrix I used. Let's re-calculate the difference.
    # lambda2 - lambda1 = sqrt((31B - 16B)^2 + 4*(6B)^2) = sqrt((15B)^2 + 144B^2) = sqrt(225B^2 + 144B^2) = sqrt(369)B.
    # Still the same. The 10Dq terms cancel out.
    
    # Is it possible that nu3 is not lambda2 - lambda1?
    # Let's re-read: nu1=9460, nu2=20160, nu3=21160.
    # If nu3 = 21160 and nu3 = 19.2 * B, then B = 1102.
    # Let's check if this makes sense. B for Co2+ is usually around 800-1000.
    # But we must check nu1 and nu2.
    # nu1 = lambda2 - 10Dq? (From our d7 hole mapping)
    # nu1 = 9460.
    # lambda2 = 10Dq + nu1 = 10700 + 9460 = 20160.
    # Also lambda2 = ( (20*Dq + 47*B) + 19.2*B ) / 2 = 10*Dq + 23.5*B + 9.6*B = 10*Dq + 33.1*B.
    # So 20160 = 10700 + 33.1*B  =>  33.1*B = 9460  =>  B = 285.
    # This B is different from the B=1102 we got from nu3 = 19.2*B.
    
    # Something is wrong. Let's use the la Grue formula or similar.
    # For d7 high spin:
    # nu1 = 8Dq - 1.5B + 0.5*sqrt( (8Dq - 1.5B)^2 + 12B^2 ) ? No.
    
    # Let's use a better source for d7 energies.
    # From "Ligand Field Theory" by Figgis:
    # For d7, the ground state is 4T1g(F).
    # nu1 (4T1g(F) -> 4T2g) = 8Dq - 1.5B + 0.5 * sqrt( (8Dq - 1.5B)^2 + 12B^2 )  -- NO.
    
    # Let's use the simplest possible relations:
    # nu1 = 8Dq - something
    # nu2 = 18Dq - something
    # nu3 = 18Dq + something
    
    # Actually, for d7:
    # nu1 = 10Dq - (mixing term)
    # nu2 = 20Dq - (mixing term)
    # nu3 = 20Dq + (mixing term)
    
    # Let's try a different approach.
    # Use the known transitions for [Co(H2O)6]2+:
    # nu1 = 9000, nu2 = 16000, nu3 = 19000.
    # Dq = 900, B = 800.
    # Let's see how these are calculated.
    # 10Dq = 9000.
    # nu1 = 10Dq - (small) = 9000.
    # nu2 = 10Dq + (something) = 16000.
    # nu3 = 10Dq + (something else) = 19000.
    # Actually, for [Co(H2O)6]2+, nu2 - nu1 = 7000. 10Dq = 9000.
    # So nu2 - nu1 is not 10Dq.
    
    # Let's use the Tanabe-Sugano equations directly.
    # I will write a function that computes nu1, nu2, nu3 from Dq and B and minimize the error.
EOF
python3 solver.py
