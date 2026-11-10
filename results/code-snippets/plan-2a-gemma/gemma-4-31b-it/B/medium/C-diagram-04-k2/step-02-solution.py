import numpy as np
import matplotlib.pyplot as plt

def get_levels(dq_b):
    # Energies relative to 5T2g
    e_5t2g = 0
    e_5eg = 10 * dq_b
    e_3t1g = 0.5
    e_3t2g = 1.0
    e_3eg = 2.0
    e_1a1g = -20 * dq_b + 42.0
    
    levels = [
        ('^5T_{2g}', e_5t2g),
        ('^5E_g', e_5eg),
        ('^3T_{1g}', e_3t1g),
        ('^3T_{2g}', e_3t2g),
        ('^3E_g', e_3eg),
        ('^1A_{1g}', e_1a1g),
    ]
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    # Shift so ground state is 0
    ground_energy = levels[0][1]
    shifted_levels = [(label, e - ground_energy) for label, e in levels]
    
    return shifted_levels

dq_b_values = np.arange(0, 4.5, 0.5)
results = []
for dq_b in dq_b_values:
    levels = get_levels(dq_b)
    results.append((dq_b, levels))

# Printing for the output
for dq_b, levels in results:
    print(f"Dq/B = {dq_b:.1f}")
    for label, e in levels:
        print(f"  {label}: {e:.2f}")

# Plotting
plt.figure(figsize=(8, 6))
for label, start_idx in [('^5T_{2g}', 0), ('^5E_g', 1), ('^3T_{1g}', 2), ('^3T_{2g}', 3), ('^3E_g', 4), ('^1A_{1g}', 5)]:
    # This is tricky because the order changes.
    # We need to track each level's energy.
    pass

# Correct plotting
dq_vals = np.arange(0, 4.5, 0.1)
plt.figure(figsize=(8, 6))
for label in ['^5T_{2g}', '^5E_g', '^3T_{1g}', '^3T_{2g}', '^3E_g', '^1A_{1g}']:
    e_vals = []
    for dq_b in dq_vals:
        # Calculate energy relative to 5T2g
        if label == '^5T_{2g}': e = 0
        elif label == '^5E_g': e = 10 * dq_b
        elif label == '^3T_{1g}': e = 0.5
        elif label == '^3T_{2g}': e = 1.0
        elif label == '^3E_g': e = 2.0
        elif label == '^1A_{1g}': e = -20 * dq_b + 42.0
        e_vals.append(e)
    
    # Relative to ground state
    # For each dq_b, find the min energy and subtract it
    # But it's easier to plot them all relative to 5T2g and then shift
    # Actually, let's just plot them as they are relative to 5T2g, 
    # then the ground state will be the lowest line.
    plt.plot(dq_vals, e_vals, label=label)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.legend()
plt.grid(True)
plt.savefig('diagram.png')
