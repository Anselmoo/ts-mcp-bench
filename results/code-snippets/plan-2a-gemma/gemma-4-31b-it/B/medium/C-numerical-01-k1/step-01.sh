cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def calculate_energies(params):
    Dq, B = params
    if Dq < 0 or B < 0:
        return 1e10
    
    # The matrix for the T1g states:
    # H11 = -15*B + 10*Dq
    # H22 = 15*B
    # H12 = 6 * np.sqrt(10) * B
    # Note: These are relative to the barycenter of the 3F term.
    # Let's use the more common matrix elements.
    # Actually, the energy levels of d2 octahedral are well known.
    # Ground state E(3T1g) = (1/2) * (10*Dq - 15*B - sqrt((10*Dq-15*B)**2 + 120*B**2)) -- NO.
    
    # Let's use a more reliable set of formulas from a textbook.
    # E(3T2g) = 10*Dq - 3*B
    # E(3A2g) = 25*Dq - 3*B
    # Wait, that's if the ground state is the barycenter.
    
    # Let's use the matrix for the T1g states:
    # H = [[10*Dq - 15*B, 6*np.sqrt(10)*B],
    #      [6*np.sqrt(10)*B, 15*B]]
    # The eigenvalues are lambda1 and lambda2.
    
    H11 = 10*Dq - 15*B
    H22 = 15*B
    H12 = 6 * np.sqrt(10) * B
    
    # Eigenvalues:
    trace = H11 + H22
    det = H11*H22 - H12**2
    
    # lambda^2 - trace*lambda + det = 0
    discriminant = np.sqrt(trace**2 - 4*det)
    l1 = (trace - discriminant) / 2
    l2 = (trace + discriminant) / 2
    
    # The other states:
    # E(3T2g) = 10*Dq - 3*B  (This is usually the first excited state)
    # E(3A2g) = 25*Dq - 3*B  (This is usually the third)
    # Wait, the E(3T2g) formula depends on the origin.
    # Let's use:
    # E(3T2g) = 10*Dq - 3*B (Wait, if we use the 3F barycenter as 0)
    # For 3F:
    # 3T1g: energy is l1
    # 3T2g: energy is -3*B + 10*Dq (relative to some origin)
    # Let's use a consistent origin.
    # In terms of 10Dq and B:
    # E(3T2g) = 10Dq - 3B
    # E(3A2g) = 25Dq - 3B
    # T1g states:
    # E(3T1g_F) = l1
    # E(3T1g_P) = l2
    # (Assuming the matrix was relative to the 3F barycenter)
    # Let's check the difference E(3A2g) - E(3T2g) = 15Dq. (Correct)
    
    # Transitions:
    nu1 = (10*Dq - 3*B) - l1
    nu2 = l2 - l1
    nu3 = (25*Dq - 3*B) - l1
    
    return np.array([nu1, nu2, nu3])

def objective(params):
    observed = np.array([20700, 30570, 42990])
    # We don't know the order of nu1, nu2, nu3. 
    # Try all permutations? No, for d2 it's usually nu1 < nu2 < nu3 or nu1 < nu3 < nu2.
    # But let's just sort them.
    calculated = calculate_energies(params)
    calculated = np.sort(calculated)
    return np.sum((calculated - observed)**2)

# Try several starting points
best_res = None
min_err = 1e20

for dq_start in [1000, 1500, 2000]:
    for b_start in [500, 700, 900]:
        res = minimize(objective, [dq_start, b_start], bounds=[(0, 5000), (0, 2000)])
        if res.fun < min_err:
            min_err = res.fun
            best_res = res

print(f"Best Dq: {best_res.x[0]:.2f}, Best B: {best_res.x[1]:.2f}, Error: {best_res.fun:.2f}")
EOF
python3 solution.py
