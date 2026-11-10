cat << 'EOF' > ts_d7.py
import numpy as np
import matplotlib.pyplot as plt

# Parameters for d7 ion
B = 859  # cm^-1
C = 3660  # cm^-1

# Dq/B values to compute
dq_over_b_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# For d7 octahedral, the quartet states are:
# From 4F: 4T1g, 4T2g, 4A2g
# From 4P: 4T1g (mixes with 4T1g from 4F)
#
# Using standard Tanabe-Sugano matrix elements for d7:
# 4T1g matrix (2x2, in units of B, with x = Dq/B):
#   | -6x      4x    |
#   |  4x    15-6x   |
# 4T2g: E/B = -2x
# 4A2g: E/B = 12x - 15

all_results = []
all_energies_for_plot = []

for dq_over_b in dq_over_b_values:
    x = dq_over_b
    
    # 4T1g matrix (2x2) - energies in units of B
    H_T1g = np.array([
        [-6*x, 4*x],
        [4*x, 15 - 6*x]
    ])
    eig_T1g = np.linalg.eigvalsh(H_T1g)
    
    # 4T2g energy (in units of B)
    E_T2g = -2*x
    
    # 4A2g energy (in units of B)
    E_A2g = 12*x - 15
    
    # Collect all energies with labels
    # The lower 4T1g eigenvalue is primarily 4T1g(F) at low field
    # The higher 4T1g eigenvalue is primarily 4T1g(P) at low field
    energies = []
    labels = []
    
    energies.append(eig_T1g[0])
    labels.append('4T1g')
    energies.append(eig_T1g[1])
    labels.append('4T1g')
    energies.append(E_T2g)
    labels.append('4T2g')
    energies.append(E_A2g)
    labels.append('4A2g')
    
    # Sort by energy
    sorted_indices = np.argsort(energies)
    sorted_energies = [energies[i] for i in sorted_indices]
    sorted_labels = [labels[i] for i in sorted_indices]
    
    # Set ground state to 0
    ground = sorted_energies[0]
    E_relative = [e - ground for e in sorted_energies]
    
    all_results.append({
        'Dq/B': dq_over_b,
        'levels': list(zip(sorted_labels, E_relative))
    })
    
    # Store for plotting (absolute E/B values)
    all_energies_for_plot.append({
        'Dq/B': dq_over_b,
        'T1g_low': eig_T1g[0] - ground,
        'T1g_high': eig_T1g[1] - ground,
        'T2g': E_T2g - ground,
        'A2g': E_A2g - ground
    })

# Print results
print("Tanabe-Sugano Diagram for d7 (B = 859 cm^-1, C = 3660 cm^-1)")
print("=" * 70)
for r in all_results:
    print(f"\nDq/B = {r['Dq/B']:.1f}")
    for i, (label, e) in enumerate(r['levels']):
        print(f"  {i+1}. {label}: E/B = {e:.6f}")

# Create plot
plt.figure(figsize=(10, 8))
colors = ['blue', 'red', 'green', 'orange']

for key in ['T1g_low', 'T1g_high', 'T2g', 'A2g']:
    energies = [d[key] for d in all_energies_for_plot]
    plt.plot(dq_over_b_values, energies, 'o-', linewidth=2, markersize=8)

plt.xlabel('Dq/B', fontsize=14)
plt.ylabel('E/B', fontsize=14)
plt.title('Tanabe-Sugano Diagram for Octahedral d⁷ Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.legend(['⁴T₁g (lower)', '⁴T₁g (upper)', '⁴T₂g', '⁴A₂g'], loc='best')
plt.xlim(-0.1, 4.1)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150)
plt.close()

print("\n\nPlot saved as diagram.png")
EOF
python3 ts_d7.py