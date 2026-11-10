cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def get_triplet_energies(Dq, B):
    # d2 Octahedral triplet energies
    # T1(F) and T1(P) mix.
    # H_T1 = [[-15*B, 6*np.sqrt(5)*B], [6*np.sqrt(5)*B, 15*B + 10*Dq]]
    # Actually, the matrix elements for d2 T1 states are:
    # <T1(F)|H|T1(F)> = -15*B + 0*Dq (if barycenter of 3F is -15B)
    # <T1(P)|H|T1(P)> = 15*B + 0*Dq
    # Let's use the energy relative to 3F barycenter.
    # T2(F) = 10*Dq
    # A2(F) = 20*Dq
    # Matrix for T1:
    # [[0, 6*np.sqrt(5)*B], [6*np.sqrt(5)*B, 30*B]]
    # This is for Dq=0. For Dq > 0, there is a shift.
    # Actually, the T1 states have no Dq shift!
    # Wait, that can't be right. Let's check the Tanabe-Sugano matrix for d2.
    # T1(F) is 0*Dq, T2(F) is 10*Dq, A2(F) is 20*Dq.
    # The T1(P) is also 0*Dq relative to the 3P barycenter.
    # Let's use:
    # E(T2) = 10*Dq
    # E(T1_low), E(T1_high) = eigenvalues of [[0, 6*np.sqrt(5)*B], [6*np.sqrt(5)*B, 30*B + 0*Dq]]
    # This is still not right because the 3P state should be shifted by Dq.
    # Let's use the formulas:
    # nu1 = E(T2) - E(T1_low)
    # nu2 = E(T1_high) - E(T1_low)
    
    # Let's try another matrix from a reliable source:
    # H_T1 = [[0, sqrt(120)*B], [sqrt(120)*B, 30*B + 10*Dq]]
    # Wait, T1(P) in d2 is 10Dq? Let's check.
    # T1(F) = 0, T2(F) = 10Dq, A2(F) = 20Dq (relative to 3F barycenter)
    # T1(P) = 30B + 0*Dq (relative to 3F barycenter)
    # Then H = [[0, sqrt(120)*B], [sqrt(120)*B, 30*B]]
    # This doesn't depend on Dq.
    
    # Let's look for "d2 octahedral Tanabe Sugano matrix"
    # From a known source:
    # E(T2) = 10*Dq
    # E(T1) matrix: [[0, 6*sqrt(5)*B], [6*sqrt(5)*B, 30*B]]
    # Wait, this is if the T1(P) state is not shifted.
    # Let me check if T1(P) is shifted.
    # For d2, the T1(P) state is actually shifted by 0*Dq.
    # Let's check that: 
    # 3P term is T1g. 3F term splits into T1g, T2g, Ag.
    # The T1(P) and T1(F) states both have the same symmetry.
    # The energy of 3P is 15B above 3F. The T1(F) is at -15B.
    # Let's use the energies from a table.
    # nu1 = 10Dq - E(T1_low)
    # nu2 = E(T1_high) - E(T1_low)
    # where E(T1) are eigenvalues of [[0, sqrt(120)*B], [sqrt(120)*B, 30*B]]
    # But that would mean nu1 depends on B and Dq, and nu2 depends only on B.
    # If nu2 = 25000 and nu1 = 17500, we can find B and Dq.
    # Let's test this.
    pass

# Let's try to solve nu2 = E(T1_high) - E(T1_low)
# E = (30*B +/- sqrt(900*B^2 + 480*B^2))/2 = (30 +/- sqrt(1380))*B / 2
# nu2 = sqrt(1380)*B = 37.148 * B
# 25000 = 37.148 * B => B = 672.7
# Then E(T1_low) = (30 - 37.148)/2 * 672.7 = -3.574 * 672.7 = -2404
# nu1 = 10*Dq - (-2404) = 17500 => 10*Dq = 15096 => Dq = 1509.6
# Now let's check if this B and Dq are reasonable for V3+.
# V3+ usually has B around 800-900. Dq around 1500-2000.
# This is close.
EOF
python3 solver.py
