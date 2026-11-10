import numpy as np
from scipy.optimize import minimize

def calculate_transitions(params):
    Dq, B = params
    if Dq <= 0 or B <= 0:
        return [1e10, 1e10, 1e10]
    
    delta = 10 * Dq
    
    # Energy of the 4F term relative to barycenter
    # For d7, ground state is T1g(F)
    # E(T1g) = 0.5*delta - 0.5*sqrt(delta**2 + 12*B**2) -- NO, let's use a better one
    
    # Let's use the matrix approach for 4F
    # H_4F = [[-3*B, 0, delta], [0, 0, 0], [delta, 0, 3*B]] -- NO
    
    # Let's use:
    # E(T2g) = delta - 1.5*B
    # E(A2g) = 1.5*delta - 1.5*B
    # E(T1g_F_no_mix) = 0.5*delta - 1.5*B - 0.5*np.sqrt((delta-3*B)**2 + 12*B**2)
    # E(T1g_P_no_mix) = 0.5*delta + 12*B
    # Then mix T1g_F and T1g_P with 6*B
    
    e_t2g = delta - 1.5 * B
    e_a2g = 1.5 * delta - 1.5 * B
    e_t1g_f = 0.5 * delta - 1.5 * B - 0.5 * np.sqrt((delta - 3*B)**2 + 12*B**2)
    e_t1g_p = 0.5 * delta + 12 * B
    
    trace = e_t1g_f + e_t1g_p
    det = e_t1g_f * e_t1g_p - (6*B)**2
    term = np.sqrt(max(0, trace**2 - 4*det))
    e_t1g_low = 0.5 * (trace - term)
    e_t1g_high = 0.5 * (trace + term)
    
    # We can have different orderings of transitions
    nu1 = e_t2g - e_t1g_low
    nu2 = e_a2g - e_t1g_low
    nu3 = e_t1g_high - e_t1g_low
    
    return [nu1, nu2, nu3]

def objective(params):
    target = [9460, 20160, 21160]
    calc = calculate_transitions(params)
    # Try different permutations of the calculated transitions
    import itertools
    best_diff = 1e20
    for p in itertools.permutations(calc):
        diff = np.sum((np.array(p) - np.array(target))**2)
        if diff < best_diff:
            best_diff = diff
    return best_diff

from scipy.optimize import differential_evolution
res = differential_evolution(objective, [(100, 2000), (100, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Transitions: {calculate_transitions(res.x)}")
