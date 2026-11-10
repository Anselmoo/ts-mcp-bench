import numpy as np
from scipy.optimize import fsolve

def get_nu2_nu1(Dq_B):
    # Dq_B = 10Dq / B
    # Use the formula for nu2/nu1 for d3
    # nu1 = 10Dq
    # nu2 = 0.5 * (15*B - 10*Dq + sqrt((10*Dq - 15*B)**2 + 120*Dq**2))
    # Let's use the eigenvalues of the matrix [[6*Dq, 6*sqrt(10)*B], [6*sqrt(10)*B, 15*B - 3*Dq]]
    # and add 6*Dq to the result.
    # Wait, the matrix was in terms of Dq = 0.5 * 10Dq_std.
    # So Dq_std = 2 * Dq_matrix.
    # Let's use a more direct approach.
    
    B = 1.0
    Dq = Dq_B / 10.0
    # Matrix for T1g
    # H = [[1.2*10*Dq, 6*sqrt(10)*B], [6*sqrt(10)*B, 15*B - 0.6*10*Dq]]
    # This is relative to the barycenter.
    # nu2 = eigenvalue - (-1.2*10*Dq) = eigenvalue + 12*Dq
    
    # Let's use Dq_std = 10*Dq
    Dq_std = Dq_B * B
    # Matrix elements relative to barycenter:
    # E(A2g) = -1.2 * Dq_std
    # E(T2g) = 0.8 * Dq_std
    # E(T1g_F) = 1.2 * Dq_std
    # E(T1g_P) = 15*B - 0.6 * Dq_std
    # Mixing = 6 * sqrt(10) * B ? No, that's for d3.
    # Actually, the mixing for d3 is V = 6 * sqrt(10) * B.
    
    # Let's use the matrix [[1.2*Dq_std, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B - 0.6*Dq_std]]
    mat = np.array([[1.2*Dq_std, 6*np.sqrt(10)*B], [6*np.sqrt(10)*B, 15*B - 0.6*Dq_std]])
    eigenvalues = np.linalg.eigvals(mat)
    # The lower eigenvalue is T1g(F)
    nu2 = min(eigenvalues) - (-1.2*Dq_std)
    nu1 = 2.0*Dq_std # Wait, nu1 = 0.8*Dq_std - (-1.2*Dq_std) = 2.0*Dq_std
    return nu2 / nu1

# Find Dq_B such that get_nu2_nu1(Dq_B) = 32500 / 26600
target = 32500 / 26600
Dq_B_guess = 15
res = fsolve(lambda x: get_nu2_nu1(x[0]) - target, [Dq_B_guess])
print(f"Dq/B ratio (10Dq/B): {res[0]}")
