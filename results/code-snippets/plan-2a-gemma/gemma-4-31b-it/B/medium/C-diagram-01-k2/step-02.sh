cat << 'EOF' > solver.py
import numpy as np
import matplotlib.pyplot as plt

def get_levels(dq_over_b, b):
    dq = dq_over_b * b
    
    # Quartet states
    e_4a2g = 0
    e_4t2g = 10 * dq
    e_4t1gf = 20 * dq
    e_4t1gp = 20 * dq + 15 * b
    
    # Doublet states
    e_2eg = 10 * dq + 20 * b
    e_2t1g = 10 * dq + 22 * b
    
    levels = [
        ('^4A_{2g}', e_4a2g),
        ('^4T_{2g}', e_4t2g),
        ('^4T_{1g}(F)', e_4t1gf),
        ('^4T_{1g}(P)', e_4t1gp),
        ('^2E_g', e_2eg),
        ('^2T_{1g}', e_2t1g),
    ]
    
    levels.sort(key=lambda x: x[1])
    
    ground = levels[0][1]
    return [(term, (e - ground) / b) for term, e in levels]

b = 828
c = 3390
dq_vals = np.arange(0, 4.1, 0.5)
results = []

plt.figure(figsize=(8, 6))
for dq_ov_b in dq_vals:
    lvls = get_levels(dq_ov_b, b)
    results.append((dq_ov_b, lvls))
    for i, (term, e_ov_b) in enumerate(lvls):
        plt.plot(dq_ov_b, e_ov_b, 'o')

# To make lines, we need to track terms
terms = ['^4A_{2g}', '^4T_{2g}', '^4T_{1g}(F)', '^4T_{1g}(P)', '^2E_g', '^2T_{1g}']
for term in terms:
    x_vals = []
    y_vals = []
    for dq_ov_b in dq_vals:
        lvls = get_levels(dq_ov_b, b)
        for t, e in lvls:
            if t == term:
                x_vals.append(dq_ov_b)
                y_vals.append(e)
                break
    plt.plot(x_vals, y_vals, label=term)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d3')
plt.legend()
plt.grid(True)
plt.savefig('diagram.png')

for dq, lvls in results:
    print(f"{dq:.1f} {lvls}")

EOF
python3 solver.py
