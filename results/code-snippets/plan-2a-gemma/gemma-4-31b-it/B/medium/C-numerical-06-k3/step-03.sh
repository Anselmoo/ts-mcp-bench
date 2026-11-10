cat << 'EOF' > solve_dq_b.py
import numpy as np
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    # Energies relative to A2g = 0 in d3
    # E(A2g) = 0
    # E(T2g) = 10 * Dq
    # e_t1g_f = 0.5 * (15*B + 10*Dq - sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    # e_t1g_p = 0.5 * (15*B + 10*Dq + sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    
    term = np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    e_a2g = 0
    e_t2g = 10 * Dq
    e_t1g_f = 0.5 * (15*B + 10*Dq - term)
    e_t1g_p = 0.5 * (15*B + 10*Dq + term)
    
    # For d7, ground state is T1g(F).
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # We need to find the correct energy relations.
    # Let's use the d3 differences:
    # E(T2g) - E(A2g) = 10*Dq
    # E(T1g_F) - E(A2g) = e_t1g_f
    # E(T1g_P) - E(A2g) = e_t1g_p
    
    # For d7:
    # Ground: T1g(F)
    # v1 = E(T2g) - E(T1g_F) = 10*Dq - e_t1g_f
    # v2 = E(A2g) - E(T1g_F) = 0 - e_t1g_f = -e_t1g_f
    # v3 = E(T1g_P) - E(T1g_F) = e_t1g_p - e_t1g_f = term
    
    # Wait, v2 = -e_t1g_f would be negative.
    # This means the d7 energies are different.
    # Let's use: E(d7, state) = E(d3, state) - E(d3, T1g_F)
    # Then:
    # v1 = 10*Dq - e_t1g_f
    # v2 = 0 - e_t1g_f = -e_t1g_f
    # v3 = e_t1g_p - e_t1g_f = term
    # Still negative.
    
    # What if the d7 states are:
    # Ground: T1g(F)
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # And E(A2g) - E(T2g) = 10*Dq (from d3)
    # So v2 = v1 + 10*Dq.
    # And v3 = term.
    # And v1 = E(T2g) - E(T1g_F) = 10*Dq - e_t1g_f (if E(A2g)=0)
    # Let's use a shift.
    # Let E(T1g_F) = 0.
    # Then E(A2g) = e_t1g_f - e_t1g_f = 0? No.
    
    # Let's use the simplest possibility:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # v2 - v1 = E(A2g) - E(T2g) = 10*Dq? No, that's d3.
    # For d7, E(A2g) - E(T2g) = 10*Dq. (since A2g is higher)
    # So v2 = v1 + 10*Dq.
    # And v3 = term = sqrt((15*B - 10*Dq)**2 + 120*Dq**2).
    # And v1 = E(T2g) - E(T1g_F).
    # From d3: E(T1g_F) - E(T2g) = e_t1g_f - 10*Dq.
    # So v1 = 10*Dq - e_t1g_f?
    
    v1 = 10*Dq - e_t1g_f
    v2 = v1 + 10*Dq
    v3 = term
    
    return (v1-9180)**2 + (v2-19550)**2 + (v3-20320)**2

res = minimize(objective, [1000, 600], bounds=[(0, 5000), (0, 5000)])
print(res.x)
EOF
python3 solve_dq_b.py
