import numpy as np
import json

def solve_d5_levels(dq_over_b):
    # Matrices for quartets
    # All quartets from t2g^4 eg^1 have LF shift -10Dq
    # except for those from t2g^3 eg^2 which have 0Dq.
    # But the free ion terms are mixtures.
    # The correct LF shifts for d5 quartets (relative to 6A1g) are:
    # 4G, 4F, 4D, 4P are primarily t2g^4 eg^1.
    # So we use -10Dq for the diagonal elements.
    
    m_t1 = np.array([
        [10.0 - 10.0*dq_over_b, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 - 10.0*dq_over_b, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 26.0 - 20.0*dq_over_b] # 4P is more like t2g^5 eg^0?
    ])
    # Actually, let's use a simpler model:
    # 6A1g: 0
    # 4T1g: min(10, 12, 26) - 10*dq_over_b
    # This is too simple.
    
    # Let's use the values from a real TS diagram for d5:
    # 6A1g is ground until Dq/B ~ 2.3.
    # Then 2T2g becomes ground.
    # The quartets are all above 6A1g for Dq/B < 2.3.
    
    # I'll use a corrected set of LF shifts.
    # For d5, the quartets' diagonal elements are:
    # 4G: -10Dq
    # 4F: -10Dq
    # 4D: -10Dq
    # 4P: -20Dq (since 4P is t2g^5)
    
    m_t1 = np.array([
        [10.0 - 10.0*dq_over_b, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 - 10.0*dq_over_b, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 26.0 - 20.0*dq_over_b]
    ])
    m_t2 = np.array([
        [10.0 - 10.0*dq_over_b, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 - 10.0*dq_over_b, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 15.0 - 10.0*dq_over_b]
    ])
    m_a2 = np.array([
        [10.0 - 10.0*dq_over_b, 6.0*dq_over_b],
        [6.0*dq_over_b, 12.0 - 10.0*dq_over_b]
    ])
    m_eg = np.array([
        [10.0 - 10.0*dq_over_b, 6.0*dq_over_b],
        [6.0*dq_over_b, 15.0 - 10.0*dq_over_b]
    ])
    
    ev_t1 = np.linalg.eigvalsh(m_t1)
    ev_t2 = np.linalg.eigvalsh(m_t2)
    ev_a2 = np.linalg.eigvalsh(m_a2)
    ev_eg = np.linalg.eigvalsh(m_eg)
    
    # 6A1g: 0
    # 2T2g: -20Dq + 32.15B
    ev_2t2 = 32.15 - 20.0*dq_over_b
    
    levels = []
    levels.append(('6A1g', 0.0))
    for i, e in enumerate(ev_t1): levels.append((f'4T1g({i})', e))
    for i, e in enumerate(ev_t2): levels.append((f'4T2g({i})', e))
    for i, e in enumerate(ev_a2): levels.append((f'4A2g({i})', e))
    for i, e in enumerate(ev_eg): levels.append((f'4Eg({i})', e))
    levels.append(('2T2g', ev_2t2))
    
    levels.sort(key=lambda x: x[1])
    ground_energy = levels[0][1]
    final_levels = []
    for term, e in levels:
        label = term.split('(')[0]
        final_levels.append({'term': label, 'e_over_b': e - ground_energy})
    return final_levels[:6]

dq_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
results = []
for dq in dq_vals:
    lvls = solve_d5_levels(dq)
    results.append({'dq_over_b': dq, 'levels': lvls})
print(json.dumps(results))
