import numpy as np
import json

def solve_d7(B, C, dq_over_b):
    Dq = dq_over_b * B
    # Quartets
    # Matrix for the two 4T1g levels
    h_t1 = np.array([[0, 6 * B * np.sqrt(2)],
                     [6 * B * np.sqrt(2), 15 * B + 10 * Dq]])
    e_t1 = np.linalg.eigvalsh(h_t1)
    
    e_t2g = 10 * Dq
    e_a2g = 20 * Dq
    
    # Doublets
    # 2Eg and 2T1g
    # P is the pairing energy offset
    P = 22 * B
    e_2eg = P - 10 * Dq
    e_2t1g = P
    
    all_levels = [
        ("^4T_{1g}", e_t1[0]),
        ("^4T_{2g}", e_t2g),
        ("^4A_{2g}", e_a2g),
        ("^4T_{1g}", e_t1[1]),
        ("^2E_g", e_2eg),
        ("^2T_{1g}", e_2t1g)
    ]
    
    all_levels.sort(key=lambda x: x[1])
    ground_e = all_levels[0][1]
    
    final_levels = []
    for l, e in all_levels:
        final_levels.append({"term": l, "e_over_b": (e - ground_e) / B})
        
    return final_levels

B = 859
C = 3660
dq_over_b_vals = np.arange(0, 4.5, 0.5)
results = []
for dq_over_b in dq_over_b_vals:
    levels = solve_d7(B, C, dq_over_b)
    results.append({"dq_over_b": float(dq_over_b), "levels": levels[:6]})

print(json.dumps(results))
