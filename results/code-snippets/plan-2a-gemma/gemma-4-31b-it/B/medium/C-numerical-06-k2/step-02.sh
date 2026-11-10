cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_d3_energies(Delta, B):
    # Delta = 10*Dq
    # E(A2g) = 0
    # E(T2g) = Delta
    # T1g states are eigenvalues of matrix:
    # [ Delta - 15*B, 6*B ]  <-- This is not it.
    # Let's use the a better matrix for T1g:
    # [ 15*B - Delta, 6*B ]
    # [ 6*B, 15*B ]
    # Let's check if B=0, Delta=0 => E=0,0. Correct.
    # Let's check B=0 => E=15B-Delta, 15B.
    
    # Correct matrix for d3 T1g states (relative to A2g):
    # H = [[15*B - Delta, 6*B], [6*B, 15*B]]
    # No, that's not it.
    
    # Let's use the formula from a reliable source for d3 quartet states:
    # E(A2g) = 0
    # E(T2g) = Delta
    # E(T1g_low) = 0.5 * (15*B + sqrt(225*B**2 + Delta**2 * 100 - 180*B*Delta)) - Delta? No.
    
    # Let's use the most basic:
    # E(A2g) = 0
    # E(T2g) = Delta
    # E(T1g_F) = 15*B - Delta
    # E(T1g_P) = 15*B + Delta? No.
    
    # Let's use the matrix from a textbook:
    # T1g matrix:
    # [ -Delta + 15*B, 6*B ]
    # [ 6*B, -Delta + 15*B + 15*B ] - No.
    
    # Let's try the "hole" approach:
    # d7 HS is hole-equivalent to d3.
    # The energy levels are identical.
    # For d3: E(A2g) < E(T2g) < E(T1g_F) < E(T1g_P)
    # For d7: E(T1g_F) < E(T2g) < E(A2g) < E(T1g_P)
    # Wait, the order is different?
    # Let's check the TS diagram for d7.
    # For d7 HS, at low Dq/B: T1g is ground.
    # Then T2g is next.
    # Then A2g.
    # Then T1g(P).
    # This matches!
    # So the energy levels of d7 HS are EXACTLY the same as d3, but in a different order?
    # No, the energy levels of d3 are:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_F) = ...
    # E(T1g_P) = ...
    # For d7, these are the same levels, but the ground state is T1g_F.
    # This means we just shift them.
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # But in d3, E(T1g_F) > E(T2g) > E(A2g).
    # This means v1 and v2 would be negative.
    # The only way this works is if the d7 levels are NOT the same as d3 levels.
    # But they ARE hole-equivalent.
    # The hole-equivalent of d3 is d7.
    # For d3: the configurations are t2g^3, t2g^2eg^1, t2g^1eg^2.
    # For d7: the configurations are t2g^6eg^1, t2g^5eg^2, t2g^4eg^3.
    # These are the same!
    # t2g^3 (d3) <-> t2g^6eg^1 (d7)
    # t2g^2eg^1 (d3) <-> t2g^5eg^2 (d7)
    # t2g^1eg^2 (d3) <-> t2g^4eg^3 (d7)
    
    # Let's calculate the energies for d7 HS:
    # Configuration 1: t2g^6eg^1. State: ^4T_{1g} (Wait, d7 low spin is ^2E, d7 HS is ^4T1g)
    # The state is ^4T_{1g}. Energy = 0 (reference)
    # Configuration 2: t2g^5eg^2. States: ^4T_{1g} and ^4T_{2g}
    # Energy = Delta
    # Configuration 3: t2g^4eg^3. State: ^4A_{2g}
    # Energy = 2*Delta
    
    # Now we use Racah parameters to split these.
    # For d7 HS:
    # E(T1g_F) = 0 (reference)
    # E(T2g) = Delta + (correction)
    # E(A2g) = 2*Delta + (correction)
    # E(T1g_P) = Delta + (correction)
    
    # Actually, let's use the known transition energies for d7 HS from a table:
    # v1 = 10*Dq - 4*B
    # v2 = 10*Dq + 2*B
    # v3 = 15*B + 10*Dq
    # I already tried these. Let's try:
    # v1 = Delta - 4*B
    # v2 = Delta + 2*B
    # v3 = 15*B + Delta
    # Wait, if v3 = 15*B + Delta and v2 = Delta + 2*B, then v3 - v2 = 13*B.
    # 20320 - 19550 = 770 => B = 59.
    # Then v2 = Delta + 2*59 = 19550 => Delta = 19432.
    # Then v1 = 19432 - 4*59 = 19196. But v1 = 9180.
    
    # What if v1 = Delta - 10*B? No.
    # What if the transitions are:
    # v1 = T1g -> T2g
    # v2 = T1g -> T1g(P)
    # v3 = T1g -> A2g
    # v3 - v2 = 20320 - 19550 = 770.
    
    # Let's use the following formulas for d7 HS:
    # v1 = Delta - 4*B
    # v2 = Delta + 2*B
    # v3 = Delta + 15*B
    # This is for d3.
    
    # Let's use the most reliable method: the T-S diagram for d7 HS.
    # v1 = E(T2g) - E(T1g)
    # v2 = E(A2g) - E(T1g)
    # v3 = E(T1g(P)) - E(T1g)
    # For d7 HS, the energies are:
    # E(T1g) = -0.5 * Delta + ...
    # E(T2g) = 0.5 * Delta + ...
    # E(A2g) = 1.5 * Delta + ...
    
    # Let's use a numerical search over B and Delta.
    # I will use a simple matrix for d7 quartet states.
    # States: T1g(F), T2g, A2g, T1g(P)
    # Energies relative to barycenter of F:
    # E(T1g_F) = -2*Dq (B=0)
    # E(T2g) = -4*Dq (B=0)
    # E(A2g) = 6*Dq (B=0)
    # E(T1g_P) = -2*Dq + 15*B (B=0)
    # This is for d3. For d7, the sign of Dq is reversed!
    # So for d7 HS:
    # E(T1g_F) = 2*Dq
    # E(T2g) = 4*Dq
    # E(A2g) = -6*Dq
    # E(T1g_P) = 2*Dq + 15*B
    # No, that's not it.
    
    # Let's use the d3 energies but with Delta = 10*Dq.
    # E(A2g) = 0
    # E(T2g) = Delta
    # T1g matrix: [[15*B - Delta, 6*B], [6*B, 15*B]]
    # This matrix gives E(T1g_low) and E(T1g_high).
    # Then v1 = E(T2g) - E(T1g_low)
    # v2 = E(A2g) - E(T1g_low)
    # v3 = E(T1g_high) - E(T1g_low)
    # Let's try this in Python.

def solve():
    from scipy.optimize import minimize
    
    def objective(params):
        Delta, B = params
        if Delta <= 0 or B <= 0: return 1e10
        
        # T1g matrix
        mat = np.array([[15*B - Delta, 6*B], [6*B, 15*B]])
        eigs = np.linalg.eigvalsh(mat)
        e_t1g_low = eigs[0]
        e_t1g_high = eigs[1]
        e_t2g = Delta
        e_a2g = 0
        
        v1 = e_t2g - e_t1g_low
        v2 = e_a2g - e_t1g_low
        v3 = e_t1g_high - e_t1g_low
        
        # Given: 9180, 19550, 20320
        # We don't know the order, but usually v1 < v2 < v3
        target = np.array([9180, 19550, 20320])
        current = np.array([v1, v2, v3])
        return np.sum((current - target)**2)

    res = minimize(objective, [15000, 1000], method='Nelder-Mead')
    print(res.x)

solve()
EOF
python3 solver.py
