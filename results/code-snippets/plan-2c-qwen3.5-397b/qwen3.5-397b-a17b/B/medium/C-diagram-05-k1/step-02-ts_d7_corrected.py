import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Parameters for d7 ion
B = 859  # cm^-1
C = 3660  # cm^-1

# Dq/B values to compute
dq_over_b_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# For d7 octahedral (high-spin, quartet states):
# From 4F (ground free-ion term): 4T1g, 4T2g, 4A2g
# From 4P: 4T1g (mixes with 4T1g from 4F)
#
# Energy expressions (relative to 4F barycenter at Dq=0):
# 4T1g(F): -6*Dq  (diagonal element)
# 4T1g(P): 15*B - 6*Dq  (diagonal element)
# Off-diagonal mixing: 4*Dq
# 4T2g(F): +2*Dq
# 4A2g(F): +12*Dq
#
# 4T1g matrix (2x2):
#   | -6*Dq      4*Dq    |
#   |  4*Dq    15*B-6*Dq |

all_results = []

# For plotting - store absolute energies
plot_data = {'T1g_1': [], 'T1g_2': [], 'T2g': [], 'A2g': []}

for dq_over_b in dq_over_b_values:
    Dq = dq_over_b * B
    x = dq_over_b  # Dq/B
    
    # 4T1g matrix (2x2) - energies in units of B
    H_T1g = np.array([
        [-6*x, 4*x],
        [4*x, 15 - 6*x]
    ])
    eig_T1g = np.linalg.eigvalsh(H_T1g)
    
    # 4T2g energy (in units of B)
    E_T2g = 2*x
    
    # 4A2g energy (in units of B)
    E_A2g = 12*x
    
    # Collect all energies with labels
    energies = []
    labels = []
    
    # Two 4T1g states from diagonalization
    energies.append(eig_T1g[0])
    labels.append('4T1g')
    energies.append(eig_T1g[1])
    labels.append('4T1g')
    
    # 4T2g
    energies.append(E_T2g)
    labels.append('4T2g')
    
    # 4A2g
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
    
    # Store for plotting
    plot_data['T1g_1'].append(eig_T1g[0] - ground)
    plot_data['T1g_2'].append(eig_T1g[1] - ground)
    plot_data['T2g'].append(E_T2g - ground)
    plot_data['A2g'].append(E_A2g - ground)

# Print results
print("Tanabe-Sugano Diagram for d7 (B = 859 cm^-1, C = 3660 cm^-1)")
print("=" * 70)
for r in all_results:
    print(f"\nDq/B = {r['Dq/B']:.1f}")
    for i, (label, e) in enumerate(r['levels']):
        print(f"  {i+1}. {label}: E/B = {e:.6f}")

# Create plot
plt.figure(figsize=(10, 8))
plt.plot(dq_over_b_values, plot_data['T1g_1'], 'bo-', linewidth=2, markersize=8, label='⁴T₁g (lower)')
plt.plot(dq_over_b_values, plot_data['T1g_2'], 'ro-', linewidth=2, markersize=8, label='⁴T₁g (upper)')
plt.plot(dq_over_b_values, plot_data['T2g'], 'go-', linewidth=2, markersize=8, label='⁴T₂g')
plt.plot(dq_over_b_values, plot_data['A2g'], 'o-', color='orange', linewidth=2, markersize=8, label='⁴A₂g')

plt.xlabel('Dq/B', fontsize=14)
plt.ylabel('E/B', fontsize=14)
plt.title('Tanabe-Sugano Diagram for Octahedral d⁷ Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.legend(loc='best')
plt.xlim(-0.1, 4.1)
plt.ylim(-1, 55)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150)
plt.close()

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")
