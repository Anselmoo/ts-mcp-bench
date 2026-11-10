import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    # Matrix for the T1 states in d2 octahedral
    # Terms: 3T1(F) and 3T1(P)
    # Energy of 3F is 0. Energy of 3P is 15B.
    # The matrix elements are from standard ligand field theory.
    # Diagonal elements:
    # E(3T1(F)) = -15B + ... wait.
    # Let's use the formula:
    # E(3T2) = -3 Dq
    # The T1 states are eigenvalues of:
    # [[ -15B + 6Dq, 6*sqrt(10)*Dq ],
    #  [ 6*sqrt(10)*Dq, 0 ]]
    # Wait, the origin matters.
    # Let's use the following matrix for d2:
    # State 1: 3T1(F)
    # State 2: 3T1(P)
    # The energies are:
    # E(3T2) = -3*Dq
    # The matrix for T1 is:
    # [[ -15*B + 6*Dq, 6*np.sqrt(10)*Dq ],
    #  [ 6*np.sqrt(10)*Dq, 0 ]]
    # No, that's not it.
    
    # Let's use the formula from a reliable source:
    # For d2, the triplet energies relative to the barycenter of 3F:
    # E(3T2) = -3*Dq
    # The T1 energies are eigenvalues of:
    # [[ -15*B + 6*Dq, 6*np.sqrt(10)*Dq ],
    #  [ 6*np.sqrt(10)*Dq, 0 ]]
    # Let's test this. At Dq=0, eigenvalues are -15B and 0.
    # E(3T1(F)) = -15B (Wait, no, 3T1(F) should be 0)
    # Let's shift it.
    # The 3F term is split into 3T1(F) and 3T2.
    # The 3F barycenter is 0.
    # E(3T1(F))_unperturbed = -6Dq
    # E(3T2)_unperturbed = -3Dq  (Wait, 3*(-6) + 3*(-3) = -18 - 9 = -27. No.)
    # 3F has L=3, so 2L+1 = 7 states.
    # In Oh, 3F -> T1g + T2g.
    # T1 has 3 states, T2 has 3 states. Total 6. (One state is missing? No, 3F is 7 states, but the 3T1 and 3T2 are the only ones in Oh? No, 3F -> T1 + T2 is not possible. F is 7, T1 is 3, T2 is 3. 3+3=6. F should be T1 + T2 + A? No.)
    # Let's check the decomposition of F in Oh: F -> T1 + T2. Wait, 3+3=6. F is 7.
    # Let me check: F is L=3. 2L+1 = 7.
    # In Oh, F splits into T1 + T2. But 3+3=6. Where is the 7th?
    # Let me check: L=3 in Oh.
    # L=3: 2L+1 = 7.
    # Decomposition: 3F -> T1 + T2. No, that's for L=2? No, L=2 is D.
    # Let's check L=3 again. 3F -> A2 + T1 + T2. (1 + 3 + 3 = 7).
    # So 3F splits into 3A2, 3T1, 3T2.
    # For d2, the ground state is 3T1(F).
    
    # Let's use the matrix for 3T1 from a reliable source:
    # The energies of 3T1(F) and 3T1(P) are roots of:
    # x^2 - (6Dq - 15B)x - 360Dq^2 = 0  (relative to barycenter of 3F)
    # E(3T2) = -3Dq (relative to barycenter of 3F)
    # Let's test this:
    # If Dq=0: x^2 + 15Bx = 0 => x=0, -15B.
    # E(3T1(F)) = 0, E(3T1(P)) = -15B.
    # Wait, if 3P is 15B ABOVE 3F, then E(3T1(P)) should be +15B.
    # So maybe x^2 - (6Dq + 15B)x - 360Dq^2 = 0?
    # Let's test Dq=0: x^2 - 15Bx = 0 => x=0, 15B. Correct.
    # So E(3T1(F)) = [ (6Dq+15B) - sqrt((6Dq+15B)^2 + 1440Dq^2) ] / 2
    # E(3T1(P)) = [ (6Dq+15B) + sqrt((6Dq+15B)^2 + 1440Dq^2) ] / 2
    # And E(3T2) = -3Dq.
    # Then nu1 = E(3T2) - E(3T1(F))
    # nu2 = E(3T1(P)) - E(3T1(F))
    
    # Let's test this for d2.
    # nu1 = -3Dq - [ (6Dq+15B) - sqrt(...) ] / 2
    # nu2 = sqrt((6Dq+15B)^2 + 1440Dq^2)
    # Let's see if this matches nu2/nu1 = 1.428.
    return 0

get_energies(1, 1)
