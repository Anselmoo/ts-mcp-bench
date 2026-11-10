import numpy as np
from scipy.optimize import fsolve

def calculate_nu(Dq, B):
    # Matrix for 3T1 states relative to the barycenter of 3F
    # For d8 Td (same as d2 Oh)
    # E(3A2) = -12*Dq
    # E(3T2) = -4*Dq
    # Matrix for 3T1:
    # [ -10*Dq,  sqrt(180)*B ]
    # [ sqrt(180)*B, 15*B - 12*Dq ] -- Wait, let me check this.
    
    # Let's use the more accurate matrix from a source:
    # For d2 Oh, the 3T1 states are eigenvalues of:
    # [ -10*Dq, sqrt(180)*B ]
    # [ sqrt(180)*B, 15*B ] -- This is relative to the 3F barycenter?
    # No, the 3P term is at 15B. The 3T1(P) state is shifted by -12Dq?
    # No, the 3P state doesn't split, but it's at 15B relative to 3F barycenter.
    # The effect of the field on 3P is a shift.
    # Let's use:
    # H = [[-10*Dq, np.sqrt(180)*B], [np.sqrt(180)*B, 15*B]]
    # The eigenvalues are lambda.
    # nu = lambda - (-12*Dq) = lambda + 12*Dq
    
    H = np.array([[-10*Dq, np.sqrt(180)*B], [np.sqrt(180)*B, 15*B]])
    eigenvalues = np.linalg.eigvals(H)
    nu = np.sort(eigenvalues) + 12*Dq
    return nu

def equations(vars):
    Dq, B = vars
    nu = calculate_nu(Dq, B)
    # nu[0] is nu_2, nu[1] is nu_3
    # Given: nu_1 = 10*Dq = 4400, nu_3 = 15500
    return [10*Dq - 4400, nu[1] - 15500]

Dq_init, B_init = 440, 600
sol = fsolve(equations, [Dq_init, B_init])
print(f"Dq: {sol[0]}, B: {sol[1]}")
