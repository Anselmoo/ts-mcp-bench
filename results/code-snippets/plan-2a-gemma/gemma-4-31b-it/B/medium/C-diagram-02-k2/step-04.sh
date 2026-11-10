cat << 'EOF' > solver.py
import numpy as np
import matplotlib.pyplot as plt

def get_energies(dq_b):
    # Interpolation based on the estimated TS values for d4, C/B=4.8
    # Dq/B: [0, 1, 2, 3, 4]
    # 5Eg: [0, 0, 0, 2, 6]
    # 5T2g: [0, 10, 20, 30, 40]
    # 3T1g: [1.8, 3, 2, 0, 0] # This is ground state relative to 5Eg at first, then becomes 0
    # Actually, let's redefine all relative to a fixed point and then shift.
    # Let E(5Eg) = -6*dq_b
    # E(5T2g) = -4*dq_b
    # E(3T1g) = 1.8 - 8*dq_b (approx)
    # E(3T2g) = 1.8 + 2*dq_b (approx)
    # E(3A2g) = 1.8 + 6*dq_b (approx)
    # E(3Eg) = 15 - 2*dq_b (approx)
    
    e_5eg = -6 * dq_b
    e_5t2g = -4 * dq_b
    e_3t1g = 1.8 - 8 * dq_b
    e_3t2g = 1.8 + 2 * dq_b
    e_3a2g = 1.8 + 6 * dq_b
    e_3eg = 15 - 2 * dq_b
    
    levels = [
        ('5Eg', e_5eg),
        ('5T2g', e_5t2g),
        ('3T1g', e_3t1g),
        ('3T2g', e_3t2g),
        ('3A2g', e_3a2g),
        ('3Eg', e_3eg),
    ]
    
    # Find the ground state
    ground_e = min(l[1] for l in levels)
    # Shift and sort
    sorted_levels = sorted([(l[0], l[1] - ground_e) for l in levels], key=lambda x: x[1])
    return sorted_levels[:6]

points = np.arange(0, 4.5, 0.5)
results = []
for p in points:
    levels = get_energies(p)
    results.append((p, levels))

# Plotting
plt.figure(figsize=(8, 6))
for name in ['5Eg', '5T2g', '3T1g', '3T2g', '3A2g', '3Eg']:
    e_vals = []
    for p in points:
        # We need the absolute energy for the plot, then shift it for each p
        e_5eg = -6 * p
        e_5t2g = -4 * p
        e_3t1g = 1.8 - 8 * p
        e_3t2g = 1.8 + 2 * p
        e_3a2g = 1.8 + 6 * p
        e_3eg = 15 - 2 * p
        
        # Ground state at this p
        gs = min(e_5eg, e_5t2g, e_3t1g, e_3t2g, e_3a2g, e_3eg)
        
        if name == '5Eg': e_vals.append(e_5eg - gs)
        elif name == '5T2g': e_vals.append(e_5t2g - gs)
        elif name == '3T1g': e_vals.append(e_3t1g - gs)
        elif name == '3T2g': e_vals.append(e_3t2g - gs)
        elif name == '3A2g': e_vals.append(e_3a2g - gs)
        elif name == '3Eg': e_vals.append(e_3eg - gs)
    plt.plot(points, e_vals, label=name)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.legend()
plt.grid(True)
plt.savefig('diagram.png')

for p, levels in results:
    print(f"{p:.1f}: {levels}")
EOF
python3 solver.py
