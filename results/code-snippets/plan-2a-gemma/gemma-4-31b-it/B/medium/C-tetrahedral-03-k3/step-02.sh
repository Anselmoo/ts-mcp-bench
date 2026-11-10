cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def get_energies(Dq, B):
    Delta = 10 * Dq
    # E(3T2) = Delta - 3B
    # E(3A2) = 1.5*Delta - 3B
    # E(3T1_F) and E(3T1_P) are eigenvalues of [[-0.5*Delta - 3*B, 2*B], [2*B, 1.5*Delta + 15*B]]
    
    e_t2 = Delta - 3*B
    e_a2 = 1.5*Delta - 3*B
    
    # Solve for T1 eigenvalues
    # H = [[-0.5*Delta - 3*B, 2*B], [2*B, 1.5*Delta + 15*B]]
    # Trace = Delta + 12*B
    # Det = (-0.5*Delta - 3*B)*(1.5*Delta + 15*B) - 4*B**2
    # Det = -0.75*Delta**2 - 7.5*Delta*B - 4.5*Delta*B - 45*B**2 - 4*B**2
    # Det = -0.75*Delta**2 - 12*Delta*B - 49*B**2
    
    trace = Delta + 12*B
    det = -0.75*Delta**2 - 12*Delta*B - 49*B**2
    
    # Eigenvalues: (trace +/- sqrt(trace^2 - 4*det)) / 2
    term = np.sqrt(max(0, trace**2 - 4*det))
    e_t1_f = (trace - term) / 2
    e_t1_p = (trace + term) / 2
    
    return e_t1_f, e_t2, e_a2, e_t1_p

def objective(vars):
    Dq, B = vars
    if Dq <= 0 or B <= 0:
        return 1e12
    
    e_t1_f, e_t2, e_a2, e_t1_p = get_energies(Dq, B)
    
    nu1 = e_t2 - e_t1_f
    nu2 = e_a2 - e_t1_f
    nu3 = e_t1_p - e_t1_f
    
    target = np.array([3600, 7870, 16410])
    current = np.array([nu1, nu2, nu3])
    
    return np.sum((target - current)**2)

res = minimize(objective, [400, 600], method='Nelder-Mead')
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Energies: {get_energies(*res.x)}")
EOF
python3 solution.py
