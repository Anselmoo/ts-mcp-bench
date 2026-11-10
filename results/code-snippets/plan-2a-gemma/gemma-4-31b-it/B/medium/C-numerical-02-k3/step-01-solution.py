import numpy as np
from scipy.optimize import minimize

def calculate_transitions(params):
    Dq, B = params
    if Dq <= 0 or B <= 0:
        return [1e10, 1e10, 1e10]
    
    delta = 10 * Dq
    
    # Energies relative to barycenter of 4F
    # These are for d3, and we adapt for d7
    # For d3: E(4A2g) = 0 (barycenter shift), E(4T2g) = delta, E(4T1g) = ...
    # Actually let's use the formulas from a reliable source:
    # E(4A2g) = 1.5*delta - 1.5*B
    # E(4T2g) = delta - 1.5*B
    # E(4T1g_F_no_mix) = 0.5*delta - 1.5*B - 0.5 * np.sqrt((delta - 3*B)**2 + 12*B**2)
    # E(4T1g_P_no_mix) = 0.5*delta + 13.5*B - 1.5*B
    
    e_a2g = 1.5 * delta - 1.5 * B
    e_t2g = delta - 1.5 * B
    
    e_t1g_f = 0.5 * delta - 1.5 * B - 0.5 * np.sqrt((delta - 3*B)**2 + 12*B**2)
    e_t1g_p = 0.5 * delta + 12 * B
    
    # Mixing of the two T1g states
    # Matrix: [[e_t1g_f, 6*B], [6*B, e_t1g_p]]
    # Eigenvalues:
    trace = e_t1g_f + e_t1g_p
    det = e_t1g_f * e_t1g_p - (6*B)**2
    
    # lambda^2 - trace*lambda + det = 0
    term = np.sqrt(max(0, trace**2 - 4*det))
    e_t1g_low = 0.5 * (trace - term)
    e_t1g_high = 0.5 * (trace + term)
    
    # Transitions from ground state e_t1g_low
    nu1 = e_t2g - e_t1g_low
    nu2 = e_a2g - e_t1g_low
    nu3 = e_t1g_high - e_t1g_low
    
    return [nu1, nu2, nu3]

def objective(params):
    target = [9460, 20160, 21160]
    calc = calculate_transitions(params)
    return np.sum((np.array(calc) - np.array(target))**2)

initial_guess = [900, 900]
res = minimize(objective, initial_guess, method='Nelder-Mead')
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Transitions: {calculate_transitions(res.x)}")
