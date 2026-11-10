import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    # For d7 high spin (hole d3 high spin)
    # State A2g energy = 0 (reference)
    # State T2g energy = 10 * Dq
    # T1g states are eigenvalues of the matrix:
    # [ -6*Dq + E_bary, 4*sqrt(10*Dq*B) ]
    # [ 4*sqrt(10*Dq*B), 15*B - 6*Dq + E_bary ]
    # However, using the T-S energy expression relative to A2g for d3:
    # E(A2g) = 0
    # E(T2g) = 10*Dq
    # E(T1g_F, P) = 0.5 * (15*B + 10*Dq +/- sqrt((15*B - 10*Dq)**2 + 120*Dq*B))
    # Note: The A2g energy in d3 is 0.
    # In d7, the ground state is T1g_F.
    # The energy difference E(A2g) - E(T2g) is 10*Dq.
    
    # Let's use the d3 levels and find the differences
    e_a2g = 0
    e_t2g = 10 * Dq
    term_t1g = 0.5 * (15*B + 10*Dq)
    disc = np.sqrt((15*B - 10*Dq)**2 + 120*Dq*B)
    e_t1g_f = term_t1g - disc
    e_t1g_p = term_t1g + disc
    
    # In d7 high spin, the ground state is T1g_F.
    # The transitions are:
    # v1: T1g_F -> T2g
    # v2: T1g_F -> A2g
    # v3: T1g_F -> T1g_P
    
    # Wait, if e_t1g_f is the ground state,
    # v1 = e_t2g - e_t1g_f
    # v2 = e_a2g - e_t1g_f
    # v3 = e_t1g_p - e_t1g_f
    
    # Let's check if this ordering makes sense.
    # v2 - v1 = e_a2g - e_t2g = -10*Dq. 
    # But we have v2 > v1.
    # This means the levels are differently ordered.
    # Let's use the d7 state ordering: T1g(F) < T2g < A2g < T1g(P)
    # So v1 = T2g - T1g(F)
    # v2 = A2g - T1g(F)
    # v3 = T1g(P) - T1g(F)
    # Then v2 - v1 = A2g - T2g.
    # In the d3 hole model, A2g is 0 and T2g is 10*Dq.
    # That would mean v2 - v1 = -10*Dq.
    # Let's re-read the hole analogy.
    # d3: A2g(0) < T2g(10Dq) < T1g_F < T1g_P
    # d7: T1g_F(0) < T2g(v1) < A2g(v2) < T1g_P(v3)
    # The gap between T2g and A2g is the same as in d3 but reversed?
    # In d3, E(T2g) - E(A2g) = 10*Dq.
    # In d7, E(A2g) - E(T2g) = 10*Dq.
    # So v2 - v1 = 10*Dq.
    
    # Let's redefine the energies for d7:
    # Let E(T1g_F) = 0.
    # Then E(T2g) = v1
    # E(A2g) = v1 + 10*Dq = v2
    # E(T1g_P) = v3
    # From d3, the T1g states are separated by 2 * disc.
    # v3 = 2 * disc = sqrt((15*B - 10*Dq)**2 + 120*Dq*B)
    # And E(T2g) - E(T1g_F) = 10*Dq - (0.5*(15*B + 10*Dq) - disc)
    # v1 = 10*Dq - 7.5*B - 5*Dq + disc = 5*Dq - 7.5*B + disc
    
    return 5*Dq - 7.5*B + disc, 15*Dq - 7.5*B + disc, 2*disc

def objective(params):
    Dq, B = params
    if Dq <= 0 or B <= 0: return 1e10
    v1, v2, v3 = get_energies(params)
    return (v1 - 8620)**2 + (v2 - 18410)**2 + (v3 - 20250)**2

res = minimize(objective, [1000, 600], method='Nelder-Mead')
print(res.x)
