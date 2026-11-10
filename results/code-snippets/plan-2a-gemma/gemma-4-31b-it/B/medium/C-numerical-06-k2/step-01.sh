cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    # Dq here is the splitting parameter, so 10*Dq is Delta_o
    # Using the matrix approach for d3/d7 quartet states
    # States: A2g, T2g, T1g(F), T1g(P)
    # Relative to A2g = 0
    # E(A2g) = 0
    # E(T2g) = 10 * Dq
    
    # The two T1g states mix
    # Matrix for T1g:
    # [[-10*Dq + 15*B, 6*B],
    #  [6*B, -10*Dq + 15*B + ...]] - No.
    
    # Let's use the standard formula for d3 energies from a reliable source:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_F) = -10*Dq + 15*B + ... mixing
    
    # Actually, for d3:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g) are eigenvalues of:
    # [ -10*Dq + 15*B, 6*B ]
    # [ 6*B, -10*Dq + 15*B + 15*B? ] - No.
    
    # Let's use the matrix from a textbook:
    # For d3 quartet states relative to A2g:
    # A2g: 0
    # T2g: 10*Dq
    # T1g(F): 15*B - 10*Dq
    # T1g(P): 15*B - 10*Dq + 15*B? No.
    
    # Let's use the correct matrix for T1g states (d3):
    # Matrix elements:
    # H11 = -10*Dq + 15*B
    # H22 = -10*Dq + 15*B + 15*B - 15*B? No.
    
    # Let's use this:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # Matrix for T1g:
    # | -10*Dq + 15*B     6*B      |
    # |     6*B      -10*Dq + 30*B | --- Not correct.
    
    # Let's use the formulas for d3 quartet states:
    # v1 = 10*Dq
    # v2 = 15*B + 10*Dq - (some mixing)
    # v3 = 15*B + 10*Dq + (some mixing)
    
    # Actually, the energies for d3 are:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_low) = (1/2) * ( 15*B + sqrt( 225*B**2 + (10*Dq)**2 * 100 - 180*B*10*Dq ) ) - 10*Dq
    # Wait, let's use the standard T-S values.
    
    # For d3:
    # nu1 = 10*Dq
    # nu2 = 15*B + nu1 - (something)
    # nu3 = 15*B + nu1 + (something)
    
    # Let's use the matrix:
    # [ 15*B - 10*Dq,   6*B ]
    # [ 6*B,           15*B - 10*Dq + 15*B ] - No.
    
    # Let's look at the d7 (HS) states. Ground state is T1g(F).
    # Transitions are to T2g, A2g, T1g(P).
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    
    # For d7, the states are:
    # E(T2g) = -4*Dq (relative to barycenter)
    # E(A2g) = 6*Dq
    # T1g matrix relative to barycenter:
    # [ -2*Dq,   6*B ]
    # [ 6*B,   -2*Dq + 15*B ]
    
    # Let's calculate the eigenvalues of the T1g matrix:
    # det([ -2*Dq - lambda, 6*B ], [ 6*B, -2*Dq + 15*B - lambda ]) = 0
    # (-2*Dq - lambda)(-2*Dq + 15*B - lambda) - (6*B)^2 = 0
    # lambda^2 - (-2*Dq + 15*B - 2*Dq)lambda + (-2*Dq)(-2*Dq + 15*B) - 36*B^2 = 0
    # lambda^2 - (-4*Dq + 15*B)lambda + (4*Dq^2 - 30*B*Dq - 36*B^2) = 0
    
    # lambda = [ (-4*Dq + 15*B) +/- sqrt( (-4*Dq + 15*B)^2 - 4(4*Dq^2 - 30*B*Dq - 36*B^2) ) ] / 2
    # lambda = [ (-4*Dq + 15*B) +/- sqrt( 16*Dq^2 + 225*B^2 - 120*B*Dq - 16*Dq^2 + 120*B*Dq + 144*B^2 ) ] / 2
    # lambda = [ (-4*Dq + 15*B) +/- sqrt( 369*B^2 ) ] / 2
    # lambda = [ -4*Dq + 15*B +/- B*sqrt(369) ] / 2
    # sqrt(369) approx 19.21
    
    # Let's re-verify the matrix elements for T1g mixing in d3/d7.
    # The mixing is actually 6*B? Let's check.
    # For d3, the matrix for T1g is:
    # [[-2*Dq, 6*B], [6*B, -2*Dq + 15*B]] is a common simplification.
    # But some sources say the mixing is different.
    
    # Let's use the transitions:
    # v1 = E(T2g) - E(T1g_low) = -4*Dq - (-4*Dq + 15*B - B*sqrt(369))/2 = ...
    # v1 = -4*Dq + 2*Dq - 7.5*B + 0.5*B*sqrt(369) = -2*Dq - 7.5*B + 9.605*B = -2*Dq + 2.105*B
    # This doesn't look right. v1 should be roughly 10*Dq.
    
    # Let's use the formula for v1, v2, v3 of d7 high spin:
    # v1 = E(T2g) - E(T1g(F))
    # v2 = E(A2g) - E(T1g(F))
    # v3 = E(T1g(P)) - E(T1g(F))
    
    # According to some tables:
    # E(T1g_F) = -2*Dq (relative to F barycenter, no mixing)
    # E(T2g) = -4*Dq
    # E(A2g) = 6*Dq
    # E(T1g_P) = -2*Dq + 15*B
    
    # With mixing:
    # T1g states are eigenvalues of [[-2*Dq, 6*B], [6*B, -2*Dq + 15*B]]
    # lambda1 (T1g_F) = -2*Dq + 7.5*B - sqrt( (7.5*B)^2 + (6*B)^2 ) = -2*Dq + 7.5*B - 9.605*B = -2*Dq - 2.105*B
    # lambda2 (T1g_P) = -2*Dq + 7.5*B + 9.605*B = -2*Dq + 17.105*B
    
    # Then:
    # v1 = E(T2g) - lambda1 = -4*Dq - (-2*Dq - 2.105*B) = -2*Dq + 2.105*B
    # v2 = E(A2g) - lambda1 = 6*Dq - (-2*Dq - 2.105*B) = 8*Dq + 2.105*B
    # v3 = lambda2 - lambda1 = 17.105*B - (-2.105*B) = 19.21*B
    
    # Wait, v1 = 9180, v2 = 19550, v3 = 20320.
    # From v3: B = 20320 / 19.21 = 1057.8
    # From v2: 8*Dq + 2.105*1057.8 = 19550 => 8*Dq = 19550 - 2226.6 = 17323.4 => Dq = 2165.4
    # Then v1 = -2*2165.4 + 2.105*1057.8 = -4330.8 + 2226.6 = -2104.2.
    # This is NOT 9180. The mixing or the formulas are wrong.
    
    # Let's rethink. The ground state of d7 HS is T1g.
    # The transitions are:
    # v1: T1g -> T2g
    # v2: T1g -> A2g
    # v3: T1g -> T1g(P)
    
    # Let's use the d3 transitions and the relation:
    # d7 (HS) is hole-equivalent to d3.
    # For d3 (ground state A2g):
    # nu1(A2g -> T2g) = 10*Dq
    # nu2(A2g -> T1g(F)) = ...
    # nu3(A2g -> T1g(P)) = ...
    
    # For d7 (ground state T1g(F)):
    # v1(T1g(F) -> T2g) = nu1 - nu2
    # v2(T1g(F) -> A2g) = -nu2
    # v3(T1g(F) -> T1g(P)) = nu3 - nu2
    # Wait, this is only if the energies are relative to A2g.
    # Let E(A2g) = 0.
    # Then nu1 = E(T2g) - 0 = 10*Dq
    # nu2 = E(T1g(F)) - 0
    # nu3 = E(T1g(P)) - 0
    # For d7, ground state is T1g(F).
    # v1 = E(T2g) - E(T1g(F)) = nu1 - nu2
    # v2 = E(A2g) - E(T1g(F)) = 0 - nu2 = -nu2
    # v3 = E(T1g(P)) - E(T1g(F)) = nu3 - nu2
    # But nu2 is the energy of T1g(F) relative to A2g, which is negative for d7 HS.
    # For d7 HS, T1g(F) is the ground state, so E(T1g(F)) < E(T2g) < E(A2g) < E(T1g(P)) usually.
    
    # Let's use the d3 energy levels again:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_low) = (1/2) * (15*B + sqrt(225*B^2 + 100*(10*Dq)^2 - 180*B*(10*Dq))) - 10*Dq (NO)
    
    # Let's use the T-S diagram for d3:
    # nu1 = 10*Dq
    # nu2 = 15*B + 10*Dq - ...
    # Actually, there is a simpler way.
    # v1 = 9180
    # v2 = 19550
    # v3 = 20320
    # v3 - v2 = 20320 - 19550 = 770 cm-1.
    # In d7 HS, v3 is T1g(F) -> T1g(P) and v2 is T1g(F) -> A2g.
    # v3 - v2 = E(T1g_P) - E(A2g).
    # For d3: E(T1g_P) - E(A2g) = nu3.
    # So nu3 = 770? No.
    
    # Let's use the following:
    # v1 = E(T2g) - E(T1g)
    # v2 = E(A2g) - E(T1g)
    # v3 = E(T1g_P) - E(T1g)
    
    # For d3 (hole equivalent):
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_low) = (1/2) [ (15*B - 10*Dq) - sqrt( (15*B - 10*Dq)^2 + 144*B^2 ) ] --- No.
    
    # Let's use the matrix for d3 quartet states:
    # A2g: 0
    # T2g: 10*Dq
    # T1g states: eigenvalues of [[ 15*B - 10*Dq, 6*B ], [ 6*B, 15*B + 10*Dq ]] --- NO.
    
    # Correct Matrix for d3 T1g states (relative to A2g):
    # [ 15*B - 10*Dq, 6*B ]
    # [ 6*B, 15*B + 10*Dq ] --- No.
    
    # Let's use a different approach.
    # For d7 high spin:
    # v1 = 10*Dq - 4*B (approx)
    # v2 = 10*Dq + 2*B (approx)
    # v3 = 15*B + 10*Dq (approx)
    
    # Let's use the transition formulas from a known d7 HS example.
    # nu1 = 10*Dq - 4*B
    # nu2 = 10*Dq + 2*B
    # nu3 = 15*B + 10*Dq
    # Let's test:
    # v2 - v1 = 6*B => 19550 - 9180 = 10370 => B = 1728
    # v3 - v2 = 13*B => 20320 - 19550 = 770 => B = 59. (Contradiction)
    
    # Let's use:
    # v1 = E(T2g) - E(T1g)
    # v2 = E(A2g) - E(T1g)
    # v3 = E(T1g(P)) - E(T1g)
    
    # In the limit of B=0:
    # E(T1g) = -2*Dq
    # E(T2g) = -4*Dq
    # E(A2g) = 6*Dq
    # E(T1g(P)) = -2*Dq
    # v1 = -2*Dq (not possible)
    
    # Let's use the correct Dq convention: Delta = 10*Dq.
    # For d7 HS:
    # E(T1g) = ground state
    # E(T2g) = ground + v1
    # E(A2g) = ground + v2
    # E(T1g(P)) = ground + v3
    
    # Using the d3 (hole) energy levels:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # T1g energies are roots of: lambda^2 - (15*B)*lambda + ( (15*B-10*Dq)(15*B+10*Dq) - 36*B^2 ) = 0? No.
    
    # Let's try this matrix for T1g states (relative to A2g):
    # [ -10*Dq + 15*B,  6*B ]
    # [ 6*B,           -10*Dq + 15*B + 15*B ] --- No.
    
    # Let's use:
    # v1 = E(T2g) - E(T1g_low)
    # v2 = E(A2g) - E(T1g_low)
    # v3 = E(T1g_high) - E(T1g_low)
    
    # From a reliable source for d3:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_low) = 15*B - 10*Dq - sqrt( (15*B - 10*Dq)^2 + ... )
    
    # Let's use the most common approximations for d7 HS:
    # v1 = 10*Dq - 4*B
    # v2 = 10*Dq + 2*B
    # v3 = 15*B + 10*Dq
    # We already saw these don't work.
    
    # What if v1 and v2 are switched? Or v2 and v3?
    # The given bands are 9180, 19550, 20320.
    # v1 = 9180
    # v2 = 19550
    # v3 = 20320
    
    # Let's use the Tanabe-Sugano diagram properties for d7.
    # v1 (T1g -> T2g)
    # v2 (T1g -> A2g)
    # v3 (T1g -> T1g(P))
    
    # For d7 HS, the ratio v2/v1 depends on Dq/B.
    # v2/v1 = 19550 / 9180 = 2.13
    # v3/v1 = 20320 / 9180 = 2.21
    
    # Let's use the Python solver to find B and Dq by searching.
    pass

EOF
python3 solver.py
