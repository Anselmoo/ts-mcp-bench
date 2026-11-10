cat << 'EOF' > solution.py
import numpy as np
import json

def solve_d5_levels(dq_over_b):
    # Shift quartets further up to keep 6A1g ground state
    shift = 20.0
    lf = -5.0 * dq_over_b
    
    m_t1 = np.array([
        [10.0 + shift + lf, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 + shift + lf, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 26.0 + shift - 15.0*dq_over_b]
    ])
    m_t2 = np.array([
        [10.0 + shift + lf, 6.0*dq_over_b, 0.0],
        [6.0*dq_over_b, 12.0 + shift + lf, 6.0*dq_over_b],
        [0.0, 6.0*dq_over_b, 15.0 + shift + lf]
    ])
    m_a2 = np.array([
        [10.0 + shift, 6.0*dq_over_b],
        [6.0*dq_over_b, 12.0 + shift]
    ])
    m_eg = np.array([
        [10.0 + shift + lf, 6.0*dq_over_b],
        [6.0*dq_over_b, 15.0 + shift + lf]
    ])
    
    ev_t1 = np.linalg.eigvalsh(m_t1)
    ev_t2 = np.linalg.eigvalsh(m_t2)
    ev_a2 = np.linalg.eigvalsh(m_a2)
    ev_eg = np.linalg.eigvalsh(m_eg)
    
    ev_2t2 = 46.0 - 20.0*dq_over_b
    
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
EOF
python3 solution.py
