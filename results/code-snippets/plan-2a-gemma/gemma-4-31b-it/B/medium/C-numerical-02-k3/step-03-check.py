import numpy as np

def calculate_transitions(params):
    Dq, B = params
    delta = 10 * Dq
    e_a2g = 1.5 * delta - 1.5 * B
    e_t2g = delta - 1.5 * B
    e_t1g_f = 0.5 * delta - 1.5 * B - 0.5 * np.sqrt((delta - 3*B)**2 + 12*B**2)
    e_t1g_p = 0.5 * delta + 12 * B
    trace = e_t1g_f + e_t1g_p
    det = e_t1g_f * e_t1g_p - (6*B)**2
    term = np.sqrt(max(0, trace**2 - 4*det))
    e_t1g_low = 0.5 * (trace - term)
    e_t1g_high = 0.5 * (trace + term)
    return [e_t2g - e_t1g_low, e_a2g - e_t1g_low, e_t1g_high - e_t1g_low]

print(calculate_transitions([930, 960]))
