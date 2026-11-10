import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    # d3 model
    # nu1 = 10*Dq
    # T1g states are eigenvalues of [[15*B, 6*sqrt(10)*B], [6*sqrt(10)*B, 15*B + 10*Dq]]
    # Wait, the matrix for T1g in d3 is usually:
    # [[ 15*B, 6*sqrt(10)*B ],
    #  [ 6*sqrt(10)*B, 15*B + 10*Dq ]]
    # Let's find eigenvalues:
    # trace = 30*B + 10*Dq
    # det = 15*B*(15*B + 10*Dq) - 360*B**2 = 225*B**2 + 150*B*Dq - 360*B**2 = 150*B*Dq - 135*B**2
    # eigenvalues = 0.5 * (trace +/- sqrt(trace**2 - 4*det))
    
    trace = 30*B + 10*Dq
    det = 150*B*Dq - 135*B**2
    disc = np.sqrt(max(0, trace**2 - 4*det))
    E_T1gF = 0.5 * (trace - disc)
    E_T1gP = 0.5 * (trace + disc)
    
    return [10*Dq - 7150, E_T1gF - 15200]

# Solve for Dq and B using nu1 and nu2
sol = fsolve(equations, [715, 900])
Dq, B = sol
print(f"Dq: {Dq}, B: {B}")

# Now check nu3
trace = 30*B + 10*Dq
det = 150*B*Dq - 135*B**2
disc = np.sqrt(max(0, trace**2 - 4*det))
E_T1gP = 0.5 * (trace + disc)
print(f"nu3: {E_T1gP}")
