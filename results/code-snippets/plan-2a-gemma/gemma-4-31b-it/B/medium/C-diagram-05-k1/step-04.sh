cat << 'EOF' > plot_diag.py
import numpy as np
import matplotlib.pyplot as plt

def solve_levels(x):
    trace = 15 - 6*x
    det = -90*x - 96*x**2
    disc = np.sqrt(trace**2 - 4*det)
    l1 = (trace - disc) / 2
    l2 = (trace + disc) / 2
    
    levels = {
        '^4T1g': l1,
        '^4T2g': 4*x,
        '^4A2g': 12*x,
        '^4T1g(P)': l2,
        '^2Eg': -18*x + 20.5,
        '^2T1g': -16*x + 22.5
    }
    
    ground_energy = min(levels.values())
    return {term: e - ground_energy for term, e in levels.items()}

x_vals = np.linspace(0, 4, 100)
results = {term: [] for term in ['^4T1g', '^4T2g', '^4A2g', '^4T1g(P)', '^2Eg', '^2T1g']}

for x in x_vals:
    res = solve_levels(x)
    for term, e in res.items():
        results[term].append(e)

plt.figure(figsize=(8, 6))
for term, e_vals in results.items():
    plt.plot(x_vals, e_vals, label=term)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d7')
plt.legend()
plt.grid(True)
plt.savefig('diagram.png')
EOF
python3 plot_diag.py
sha256sum diagram.png
