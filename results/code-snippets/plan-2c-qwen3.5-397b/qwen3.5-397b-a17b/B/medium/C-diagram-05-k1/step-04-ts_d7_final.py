import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Parameters for d7 ion
B = 859  # cm^-1
C = 3660  # cm^-1
C_over_B = C / B  # ≈ 4.2608

# Dq/B values to compute
dq_over_b_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

# Free-ion term energies (relative to 4F ground, in E/B units):
# 4F: 0
# 4P: 15
# 2P: 15 + 5*(C/B) = 15 + 5*4.2608 = 36.304
# 2G: 12 + 5*(C/B) = 33.304
# 2H: 12 + 5*(C/B) = 33.304

E_2P_B = 15 + 5 * C_over_B   # ≈ 36.304
E_2G_B = 12 + 5 * C_over_B   # ≈ 33.304
E_2H_B = 12 + 5 * C_over_B   # ≈ 33.304

# Octahedral splitting (relative to term barycenter, in units of Dq):
# 2P -> 2T1g (-4Dq), 2T2g (+6Dq)  [T1 + T2 for P term]
# 2G -> 2Eg (+12Dq), 2T2g (-8Dq)
# 2H -> 2Eg (-10Dq), 2T1g (-4Dq), 2T2g (+6Dq)

all_results = []

for dq_over_b in dq_over_b_values:
    x = dq_over_b  # Dq/B
    
    # === QUARTET STATES ===
    # 4T1g matrix (2x2)
    H_T1g = np.array([
        [-6*x, 4*x],
        [4*x, 15 - 6*x]
    ])
    eig_T1g = np.linalg.eigvalsh(H_T1g)
    
    # 4T2g and 4A2g
    E_T2g = 2*x
    E_A2g = 12*x
    
    # === DOUBLET STATES ===
    # From 2P
    E_2T1g_2P = E_2P_B - 4*x
    E_2T2g_2P = E_2P_B + 6*x
    
    # From 2G
    E_2Eg_2G = E_2G_B + 12*x
    E_2T2g_2G = E_2G_B - 8*x
    
    # From 2H
    E_2Eg_2H = E_2H_B - 10*x
    E_2T1g_2H = E_2H_B - 4*x
    E_2T2g_2H = E_2H_B + 6*x
    
    # Collect ALL energies with labels
    energies = []
    labels = []
    
    # Quartets
    energies.append(eig_T1g[0])
    labels.append('4T1g')
    energies.append(eig_T1g[1])
    labels.append('4T1g')
    energies.append(E_T2g)
    labels.append('4T2g')
    energies.append(E_A2g)
    labels.append('4A2g')
    
    # Doublets
    energies.append(E_2T1g_2P)
    labels.append('2T1g')
    energies.append(E_2T2g_2P)
    labels.append('2T2g')
    energies.append(E_2Eg_2G)
    labels.append('2Eg')
    energies.append(E_2T2g_2G)
    labels.append('2T2g')
    energies.append(E_2Eg_2H)
    labels.append('2Eg')
    energies.append(E_2T1g_2H)
    labels.append('2T1g')
    energies.append(E_2T2g_2H)
    labels.append('2T2g')
    
    # Sort by energy
    sorted_indices = np.argsort(energies)
    sorted_energies = [energies[i] for i in sorted_indices]
    sorted_labels = [labels[i] for i in sorted_indices]
    
    # Set ground state to 0
    ground = sorted_energies[0]
    E_relative = [e - ground for e in sorted_energies]
    
    # Take lowest 6 levels
    lowest_6 = list(zip(sorted_labels[:6], E_relative[:6]))
    
    all_results.append({
        'Dq/B': dq_over_b,
        'levels': lowest_6
    })

# Print results
print("Tanabe-Sugano Diagram for d7 (B = 859 cm^-1, C = 3660 cm^-1)")
print("=" * 70)
for r in all_results:
    print(f"\nDq/B = {r['Dq/B']:.1f}")
    for i, (label, e) in enumerate(r['levels']):
        print(f"  {i+1}. {label}: E/B = {e:.6f}")

# Create plot
plot_data = {'T1g_1': [], 'T1g_2': [], 'T2g': [], 'A2g': []}
for dq_over_b in dq_over_b_values:
    x = dq_over_b
    H_T1g = np.array([[-6*x, 4*x], [4*x, 15 - 6*x]])
    eig_T1g = np.linalg.eigvalsh(H_T1g)
    E_T2g = 2*x
    E_A2g = 12*x
    
    energies = [eig_T1g[0], eig_T1g[1], E_T2g, E_A2g]
    ground = min(energies)
    
    plot_data['T1g_1'].append(eig_T1g[0] - ground)
    plot_data['T1g_2'].append(eig_T1g[1] - ground)
    plot_data['T2g'].append(E_T2g - ground)
    plot_data['A2g'].append(E_A2g - ground)

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
