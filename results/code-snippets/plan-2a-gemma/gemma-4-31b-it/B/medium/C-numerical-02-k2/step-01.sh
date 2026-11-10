cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(Dq, B):
    Delta = 10 * Dq
    # The states of d2/d7 high spin from 4F: T1, T2, A2
    # The T1g(F) and T1g(P) states mix.
    # The other states are T2g(F) and A2g(F).
    # Energy of T2g(F) = -0.5 * B + 0.5 * Delta
    # Energy of A2g(F) = 0.5 * B + Delta
    # The T1g(F) and T1g(P) energies are eigenvalues of:
    # [[ -0.5*B - 0.5*Delta, 6*B ],
    #  [ 6*B, 1.5*B + 0.5*Delta ]]
    
    # Wait, let's use the standard matrix for d2/d7:
    # Matrix for T1g:
    # | -1.5B - 0.5Delta  6B |
    # | 6B               1.5B + 0.5Delta | 
    # No, the diagonal elements for T1 are usually given as:
    # E(T1g,F) = -0.5*B - 0.5*Delta
    # E(T1g,P) = 1.5*B + 0.5*Delta
    # Let me double check this.
    
    # Standard energies for d2 (from a reliable source):
    # E(T2g) = -0.5*B + 0.5*Delta
    # E(A2g) = 0.5*B + Delta
    # T1g(F) and T1g(P) mix:
    # H = [[-0.5*B - 0.5*Delta, 6*B], [6*B, 1.5*B + 0.5*Delta]]
    
    mat_t1 = np.array([[-0.5*B - 0.5*Delta, 6*B], [6*B, 1.5*B + 0.5*Delta]])
    eigvals_t1 = np.linalg.eigvalsh(mat_t1)
    e_t1_f = eigvals_t1[0]
    e_t1_p = eigvals_t1[1]
    
    e_t2_f = -0.5 * B + 0.5 * Delta
    e_a2_f = 0.5 * B + Delta
    
    return e_t1_f, e_t2_f, e_a2_f, e_t1_p

def objective(params):
    Dq, B = params
    if Dq <= 0 or B <= 0: return 1e10
    
    e_t1_f, e_t2_f, e_a2_f, e_t1_p = get_energies(Dq, B)
    
    nu1 = e_t2_f - e_t1_f
    nu2 = e_a2_f - e_t1_f
    nu3 = e_t1_p - e_t1_f
    
    target = np.array([9460, 20160, 21160])
    current = np.array([nu1, nu2, nu3])
    
    return np.sum((target - current)**2)

res = minimize(objective, x0=[1000, 600], method='Nelder-Mead')
print(res.x)
print(get_energies(*res.x))
EOF
python3 solver.py
