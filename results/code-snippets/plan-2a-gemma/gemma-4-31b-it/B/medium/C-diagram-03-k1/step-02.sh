cat << 'EOF' > solution.py
import numpy as np
import json

def solve_d5_levels(dq_over_b):
    # Matrices for quartets
    # 4T1g: from 4G, 4F, 4P
    m_t1 = np.array([
        [10.0 - 6.0*dq_over_b, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 - 6.0*dq_over_b, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 26.0 - 18.0*dq_over_b]
    ])
    
    # 4T2g: from 4G, 4F, 4D
    m_t2 = np.array([
        [10.0 - 6.0*dq_over_b, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 - 6.0*dq_over_b, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 15.0 - 6.0*dq_over_b]
    ])
    
    # 4A2g: from 4G, 4F
    m_a2 = np.array([
        [10.0, 6.0*dq_over_b],
        [6.0*dq_over_b, 12.0]
    ])
    
    # 4Eg: from 4G, 4D
    m_eg = np.array([
        [10.0 - 6.0*dq_over_b, 6.0*dq_over_b],
        [6.0*dq_over_b, 15.0 - 6.0*dq_over_b]
    ])
    
    ev_t1 = np.linalg.eigvalsh(m_t1)
    ev_t2 = np.linalg.eigvalsh(m_t2)
    ev_a2 = np.linalg.eigvalsh(m_a2)
    ev_eg = np.linalg.eigvalsh(m_eg)
    
    # 6A1g ground state
    # 2T2g state (C=4.43B)
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
        # Removing the index from term label
        label = term.split('(')[0]
        final_levels.append({'term': label, 'e_over_b': e - ground_energy})
        
    return final_levels[:6]

dq_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
results = []

for dq in dq_vals:
    lvls = solve_d5_levels(dq)
    results.append({'dq_over_b': dq, 'levels': lvls})

print(json.dumps(results))
EOF
python3 solution.py
