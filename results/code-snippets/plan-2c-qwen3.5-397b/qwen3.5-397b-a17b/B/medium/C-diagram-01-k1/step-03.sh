cat > ts_d3_correct.py << 'EOF'
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
    
    Energies are relative to the ground state (4A2g) at each Dq/B.
    
    For d3, the free ion terms relative to 4F ground term:
    - 4P: 15B
    - 2G: 9B + 3C (from Racah analysis)
    - 2H: 9B + 3C
    - 2P: 18B + 3C
    - 2D, 2F: higher
    
    With C/B = 4.094:
    - 2G, 2H: 9 + 3*4.094 = 21.28B above 4F
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # === QUARTET STATES ===
    # Reference: 4A2g is set to E/B = 0 at all Dq/B
    
    # 4A2g: ground state, always at 0 by convention
    levels.append((0.0, '4A2g'))
    
    # 4T2g: from 4F, at 10Dq above 4A2g
    e_4t2g = 10 * x
    levels.append((e_4t2g, '4T2g'))
    
    # 4T1g states: mixing between 4T1g(F) and 4T1g(P)
    # Relative to 4A2g:
    # 4T1g(F): 18Dq -> 18x
    # 4T1g(P): 15B + 18Dq -> 15 + 18x
    # Off-diagonal mixing: 4Dq -> 4x
    
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))  # Lower 4T1g
    levels.append((eig_4t1g[1], '4T1g'))  # Upper 4T1g
    
    # === DOUBLE STATES ===
    # Correct free ion term energies relative to 4F (in units of B):
    # Using Racah parameter formulas for d3:
    # E(2G) = E(4F) + 9B + 3C
    # E(2H) = E(4F) + 9B + 3C
    # E(2P) = E(4F) + 18B + 3C
    
    E_2G_4F = 9 + 3*C_over_B  # = 9 + 12.283 = 21.283
    E_2H_4F = 9 + 3*C_over_B  # Same as 2G
    E_2P_4F = 18 + 3*C_over_B  # = 18 + 12.283 = 30.283
    
    # 2Eg matrix (from 2G and 2H)
    # Crystal field splitting within 2G: 2Eg at +2Dq, 2T1g at -Dq, 2T2g at +Dq
    # Crystal field splitting within 2H: 2Eg at -3Dq, 2T1g at +Dq, 2T2g at +2Dq
    # Mixing between 2G and 2H components: ~2*sqrt(6)*Dq
    
    H_2eg = np.array([[E_2G_4F + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H_4F - 3*x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g matrix (from 2G and 2H)
    H_2t1g = np.array([[E_2G_4F - x, 2*x], 
                       [2*x, E_2H_4F + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g matrix (from 2G and 2H)
    H_2t2g = np.array([[E_2G_4F + x, x], 
                       [x, E_2H_4F + 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    # Higher doublets (2P, 2F derived)
    # 2T1g from 2P (approximately constant, high energy)
    levels.append((E_2P_4F, '2T1g'))
    
    # 2A2g from 2F (at ~20B + C above 4F)
    E_2F_4F = 20 + C_over_B
    levels.append((E_2F_4F + 6*x, '2A2g'))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

# Compute and print energies for each Dq/B
results = []
print("Tanabe-Sugano Diagram for d³ Octahedral (B = 828 cm⁻¹, C = 3390 cm⁻¹)")
print("="*70)

for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    results.append((dq_over_b, levels))
    print(f"\nDq/B = {dq_over_b:.1f}:")
    for i, (e, label) in enumerate(levels):
        print(f"  Level {i+1}: {label}, E/B = {e:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(12, 8))

# Collect all levels for plotting
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
ax.set_title('Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹, C/B = 4.094)', fontsize=14)
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-1, 50)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")
EOF
python3 ts_d3_correct.py