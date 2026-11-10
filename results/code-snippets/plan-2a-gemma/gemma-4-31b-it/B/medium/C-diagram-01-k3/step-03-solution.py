import numpy as np
import json

B = 828
C = 3390
dq_b_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

for dq_b in dq_b_vals:
    dq = dq_b * B
    
    if dq_b == 0:
        # At Dq/B = 0, use the free-ion terms split by symmetry
        # 4A2g, 4T2g, 4T1g(F) are at 0
        # 4T1g(P) is at 15B
        # 2G terms are at -3B + 12C
        e_gnd = 0
        levels = [
            ("4A2g", 0.0),
            ("4T2g", 0.0),
            ("4T1g", 0.0),
            ("4T1g", 15.0 * B),
            ("2T1g", -3*B + 12*C),
            ("2T2g", -3*B + 12*C)
        ]
    else:
        # Quartets
        e_gnd = -15 * dq
        # 4T2g
        e_4t2g = -5 * dq
        # 4T1g mixing
        mat = np.array([[15*dq, 3*B], [3*B, 15*B]])
        eigvals = np.linalg.eigvalsh(mat)
        
        quartets = [
            ("4A2g", e_gnd),
            ("4T2g", e_4t2g),
            ("4T1g", eigvals[0]),
            ("4T1g", eigvals[1])
        ]
        
        # Doublets from 2G
        e_2g_centroid = -3*B + 12*C
        # Shifts for G -> A1, E, T1, T2
        # Normalized shifts: A1: 7.33, E: 1.33, T1: -2.67, T2: -0.67
        doublets_2g = [
            ("2T1g", e_2g_centroid - 2.6666666666666665 * dq),
            ("2T2g", e_2g_centroid - 0.6666666666666665 * dq),
            ("2Eg", e_2g_centroid + 1.3333333333333333 * dq),
            ("2A1g", e_2g_centroid + 7.333333333333333 * dq)
        ]
        
        all_levels = []
        for term, e in quartets:
            all_levels.append((term, e - e_gnd))
        for term, e in doublets_2g:
            all_levels.append((term, e - e_gnd))
        
        all_levels.sort(key=lambda x: x[1])
        levels = all_levels[:6]
    
    # Convert to E/B
    eb_levels = []
    for term, e in levels:
        eb_levels.append({"term": term, "e_over_b": e / B})
    
    results.append({"dq_over_b": dq_b, "levels": eb_levels})

print(json.dumps(results))
