cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt

def compute_levels(x):
    e_5eg = 0
    e_5t2g = 10 * x
    e_3t1g_f_unc = 12 - 4 * x
    e_3t2g_f = 12 + 2 * x
    e_3a2g_f = 12 + 6 * x
    e_3t1g_p_unc = 24 - 4 * x
    
    # Mixing of the two 3T1g terms
    mean = (e_3t1g_f_unc + e_3t1g_p_unc) / 2
    diff = (e_3t1g_f_unc - e_3t1g_p_unc) / 2
    # mixing V = 5
    v = 5
    lambda1 = mean - np.sqrt(diff**2 + v**2)
    lambda2 = mean + np.sqrt(diff**2 + v**2)
    
    levels = [
        ('^5Eg', e_5eg),
        ('^5T2g', e_5t2g),
        ('^3T1g', lambda1),
        ('^3T2g', e_3t2g_f),
        ('^3A2g', e_3a2g_f),
        ('^3T1g_P', lambda2)
    ]
    
    # Sort and make ground state 0
    sorted_levels = sorted(levels, key=lambda x: x[1])
    ground_energy = sorted_levels[0][1]
    final_levels = []
    for term, energy in sorted_levels:
        final_levels.append({'term': term, 'e_over_b': round(energy - ground_energy, 2)})
        
    return final_levels

dq_b_values = np.arange(0, 4.5, 0.5)
results = []

for x in dq_b_values:
    levels = compute_levels(x)
    results.append({'dq_over_b': x, 'levels': levels})

# Save plot
plt.figure(figsize=(8, 6))
for term_idx in range(6):
    x_vals = []
    y_vals = []
    for x in dq_b_values:
        levels = compute_levels(x)
        # This is tricky because the order changes. 
        # We need to track the terms.
        # But for a simple plot, we can just use the sorted indices.
        y_vals.append(levels[term_idx]['e_over_b'])
        x_vals.append(x)
    plt.plot(x_vals, y_vals, label=None)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('d4 Octahedral Tanabe-Sugano Diagram (approx)')
plt.grid(True)
plt.savefig('diagram.png')

import json
print(json.dumps(results))
EOF
python3 solution.py
