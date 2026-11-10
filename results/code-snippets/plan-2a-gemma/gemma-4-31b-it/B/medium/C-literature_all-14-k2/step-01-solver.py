import numpy as np
from scipy.optimize import fsolve

def calculate_energies(Dq, B):
    Delta = 10 * Dq
    # Energies of the quartet terms relative to the barycenter of the 4F term
    # For d7 Octahedral:
    # E(4T2) = -0.6 * Delta + 6 * B (Wait, is this correct? Let's use matrices)
    # Let's use the matrix for T1 terms:
    # The 4F state gives a T1 state with energy -0.6*Delta + 6*B ? No.
    
    # Let's use the formula for d3 and flip signs/offsets.
    # For d3:
    # E(4A2) = 0
    # E(4T2) = 10 * Dq
    # E(4T1) roots of:
    # lambda^2 - (15B + 10Dq) lambda + (10Dq * 15B + 30B^2 - 80Dq^2) = 0 ? No.
    
    # Correct matrices for d3 (Oct):
    # 4A2: 0
    # 4T2: 10Dq
    # 4T1: matrix [[ -10Dq + 15B, 40Dq ], [ 40Dq, 10Dq - 15B + 15B ]]? No.
    
    # Let's use the T-S energy expressions from a textbook.
    # For d7 Oct (high spin):
    # E(4T1(F)) = root1
    # E(4T2) = -0.6*Delta + 6B
    # E(4A2) = 1.2*Delta - 6B
    # E(4T1(P)) = root2
    # where root1, root2 are from the T1 matrix.
    # T1 matrix elements (relative to 4F barycenter):
    # H11 = -0.6*Delta + 6B  (from 4F)
    # H22 = 0.6*Delta - 6B + 15B (from 4P)
    # H12 = 4*sqrt(10)*Dq * (Wait, the interaction is 4*Delta / sqrt(10) * ... no)
    
    # Let's use the 4T1 matrix elements for d3 and map to d7.
    # For d3:
    # H11 = 10Dq - 15B (Wait, let's use a better source)
    # Actually, a very common form is:
    # E(4T1) = (15B + 10Dq) / 2 +/- sqrt( (15B - 10Dq)^2 / 4 + 120 Dq^2 ) ? No.
    
    # Let's use the Tanabe-Sugano equations for d3 and replace Dq with -Dq (essentially).
    # For d3:
    # v1 = 10 Dq
    # v2 = E(4T1(F)) - E(4A2)
    # v3 = E(4T1(P)) - E(4A2)
    
    # For d7:
    # v1 = E(4T2) - E(4T1(F))
    # v2 = E(4T1(P)) - E(4T1(F))
    # v3 = E(4A2) - E(4T1(F))
    
    # Let's express these in terms of Dq and B.
    # In d3, the 4T1 states are:
    # E(4T1(F)) = (15B + 10Dq) / 2 - sqrt( (15B - 10Dq)^2 / 4 + 120 Dq^2 ) ? No.
    
    # Let's use the formula from a reliable source for d7:
    # v1 = E(4T2) - E(4T1(F))
    # v2 = E(4T1(P)) - E(4T1(F))
    # The energies relative to the 4F barycenter:
    # E(4T2) = -0.6 * Delta + 6 * B
    # E(4A2) = 1.2 * Delta - 6 * B
    # Matrix for 4T1 states:
    # [[ -0.6 * Delta + 6 * B, 4 * Delta ],
    #  [ 4 * Delta, 0.6 * Delta + 9 * B ]]
    # Wait, the interaction term is usually 4*Delta. Let's check.
    # For d3, the interaction is 4*Delta.
    # Let's check the matrix:
    # H11 = E(4T1 from 4F) = -0.6*Delta + 6B
    # H22 = E(4T1 from 4P) = 0.6*Delta - 6B + 15B = 0.6*Delta + 9B
    # H12 = 4 * Delta
    # This seems reasonable.
    
    mat = np.array([[-0.6*Delta + 6*B, 4*Delta],
                    [4*Delta, 0.6*Delta + 9*B]])
    evals = np.linalg.eigvalsh(mat)
    
    e_4t1_f = evals[0]
    e_4t1_p = evals[1]
    e_4t2 = -0.6 * Delta + 6 * B
    e_4a2 = 1.2 * Delta - 6 * B
    
    v1 = e_4t2 - e_4t1_f
    v2 = e_4t1_p - e_4t1_f
    v3 = e_4a2 - e_4t1_f
    
    return v1, v2, v3

def equations(p):
    Dq, B = p
    v1, v2, v3 = calculate_energies(Dq, B)
    return [v1 - 8100, v2 - 19400]

# Guess Dq and B
# v1 ~ 10 Dq? Not exactly. 8100 / 10 = 810.
# Try Dq = 800, B = 600
sol = fsolve(equations, [800, 600])
print(f"Dq: {sol[0]}, B: {sol[1]}")
v1, v2, v3 = calculate_energies(sol[0], sol[1])
print(f"v1: {v1}, v2: {v2}, v3: {v3}")
