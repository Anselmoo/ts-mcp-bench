import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Parameters for d3 ion
B = 828  # cm^-1
C = 3390  # cm^-1
C_over_B = C / B  # = 4.094202898550725

# Dq/B values to compute
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

def d3_energies(dq_over_b, C_over_B=4.094202898550725):
    """
    Compute energy levels for d3 octahedral complex.
    Returns list of (energy/B, term_label) tuples for lowest 6 levels.
    """
    x = dq_over_b
    levels = []
    
    # === QUARTET STATES ===
    levels.append((0.0, '4A2g'))
    levels.append((10 * x, '4T2g'))
    
    # 4T1g mixing matrix
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))
    levels.append((eig_4t1g[1], '4T1g'))
    
    # === DOUBLE STATES ===
    # Free ion energies relative to 4F (in units of B):
    # E(2G) - E(4F) = 6B + 3C for d3
    E_2G = 6 + 3*C_over_B  # = 18.2826
    E_2H = 6 + 3*C_over_B
    
    # Crystal field splitting (corrected coefficients):
    # 2G: 2Eg +2Dq, 2T1g -Dq, 2T2g +Dq
    # 2H: 2Eg +Dq, 2T1g +Dq, 2T2g -2Dq
    
    # 2Eg matrix
    H_2eg = np.array([[E_2G + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H + x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g matrix
    H_2t1g = np.array([[E_2G - x, 2*x], 
                       [2*x, E_2H + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g matrix
    H_2t2g = np.array([[E_2G + x, x], 
                       [x, E_2H - 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

# Compute and print results
results = []
print("Tanabe-Sugano Diagram for d³ Octahedral")
print("B = 828 cm⁻¹, C = 3390 cm⁻¹, C/B = {:.4f}".format(C_over_B))
print("="*70)

for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    results.append((dq_over_b, levels))
    print(f"\nDq/B = {dq_over_b:.1f}:")
    for i, (e, label) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {e:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(12, 8))

all_levels = {i: {'x': [], 'y': [], 'label': ''} for i in range(6)}

for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    for i, (e, label) in enumerate(levels):
        all_levels[i]['x'].append(dq_over_b)
        all_levels[i]['y'].append(e)
        if dq_over_b == 0:
            all_levels[i]['label'] = label

colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown']

for i in range(6):
    ax.plot(all_levels[i]['x'], all_levels[i]['y'], '-', 
            color=colors[i], linewidth=2, label=all_levels[i]['label'])
    ax.plot(all_levels[i]['x'], all_levels[i]['y'], 'o', 
            color=colors[i], markersize=8)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹)', fontsize=14)
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-1, 45)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")

# Output results in structured format for verification
print("\n\n=== SUMMARY ===")
for dq_over_b, levels in results:
    print(f"Dq/B = {dq_over_b:.1f}:")
    for e, label in levels:
        print(f"  {label}: {e:.4f}")
