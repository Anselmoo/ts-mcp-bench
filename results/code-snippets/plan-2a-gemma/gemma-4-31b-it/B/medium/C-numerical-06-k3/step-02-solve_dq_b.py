import numpy as np
from scipy.optimize import fsolve

def get_v(vars):
    Dq, B = vars
    
    # Energies for d3 relative to A2g = 0
    # E(A2g) = 0
    # E(T2g) = 10 * Dq
    # E(T1g_F) = 0.5 * (15*B + 10*Dq - sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    # E(T1g_P) = 0.5 * (15*B + 10*Dq + sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    
    term = np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    e_a2g = 0
    e_t2g = 10 * Dq
    e_t1g_f = 0.5 * (15*B + 10*Dq - term)
    e_t1g_p = 0.5 * (15*B + 10*Dq + term)
    
    # Now for d7, we must shift these.
    # The ground state is T1g(F).
    # The energy differences are:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # But wait, if e_t1g_f is the ground state, its energy is the lowest.
    # In d3, e_a2g is the lowest.
    # So the energies for d7 are:
    # E(T1g_F) = 0
    # E(T2g) = e_t2g - e_t1g_f
    # E(A2g) = e_a2g - e_t1g_f  <-- This will be negative!
    # This means T1g(F) is NOT the ground state in d3.
    # Let's re-evaluate: e_t1g_f = 0.5 * (19000 - 11000) = 4000.
    # So e_a2g(0) < e_t1g_f(4000) < e_t2g(10000) < e_t1g_p(15000).
    # For d7, the order is reversed.
    # The energy differences between states are the same.
    # The states in d7 are:
    # Ground: T1g(F)
    # Next: T2g
    # Next: A2g
    # Next: T1g(P)
    # No, that's not possible. If the differences are the same,
    # E(T2g) - E(T1g_F) in d7 = E(T1g_F) - E(T2g) in d3?
    # Let's use the property:
    # E(d7, state) = -E(d3, state) + constant.
    # E(d3, A2g) = 0
    # E(d3, T2g) = 10*Dq
    # E(d3, T1g_F) = e_t1g_f
    # E(d3, T1g_P) = e_t1g_p
    # Then:
    # E(d7, A2g) = 0
    # E(d7, T2g) = -10*Dq
    # E(d7, T1g_F) = -e_t1g_f
    # E(d7, T1g_P) = -e_t1g_p
    # This makes e_t1g_p the ground state. That's not right.
    
    # Let's use the actual energy expressions for d7:
    # Ground state: T1g(F)
    # E(T1g_F) = 0
    # E(T2g) = 8*Dq + (something)
    
    # Let's try this:
    # v1 = 8*Dq
    # v2 = 8*Dq + 10*Dq = 18*Dq ?
    # No.
    
    # Let's go back to:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # We know E(A2g) - E(T2g) = 10*Dq (from d3)
    # So v2 - v1 = 10*Dq.
    # And E(T1g_P) - E(T1g_F) = term = sqrt((15*B - 10*Dq)**2 + 120*Dq**2)
    # So v3 = term.
    # And E(T2g) - E(T1g_F)? 
    # In d3: E(T1g_F) - E(T2g) = e_t1g_f - 10*Dq.
    # For d7: E(T2g) - E(T1g_F) = 10*Dq - e_t1g_f.
    
    v3 = term
    v1 = 10*Dq - e_t1g_f
    v2 = v1 + 10*Dq
    
    return [v1 - 9180, v2 - 19550, v3 - 20320]

# solve:
# v2 - v1 = 10*Dq = 19550 - 9180 = 10370 => Dq = 1037
# v3 = 20320 => term = 20320
# e_t1g_f = 0.5 * (15*B + 10*Dq - 20320)
# v1 = 10*Dq - 0.5 * (15*B + 10*Dq - 20320) = 9180
# 10370 - 7.5*B - 5*Dq + 10160 = 9180
# 10370 - 7.5*B - 5185 + 10160 = 9180
# 15345 - 7.5*B = 9180
# 7.5*B = 15345 - 9180 = 6165
# B = 6165 / 7.5 = 822
# Let's check Dq = 1037, B = 822 with v3 = 20320.
# term = sqrt((15*822 - 10*1037)**2 + 120*1037**2)
# term = sqrt((12330 - 10370)**2 + 120*1075369)
# term = sqrt(1960^2 + 129044280) = sqrt(3841600 + 129044280) = sqrt(132885880) = 11527
# This is NOT 20320.
# So v2 - v1 = 10*Dq might be wrong.
