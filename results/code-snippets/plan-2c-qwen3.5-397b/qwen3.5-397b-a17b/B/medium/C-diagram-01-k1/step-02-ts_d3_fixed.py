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
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # === QUARTET STATES ===
    # Reference: 4A2g is set to E/B = 0 at all Dq/B
    
    # 4A2g: ground state, always at 0 by convention
    levels.append((0.0, '4A2g'))
    
    # 4T2g: from 4F, at 10Dq above 4A2g
    # E(4T2g) - E(4A2g) = (-2Dq) - (-12Dq) = 10Dq
    e_4t2g = 10 * x
    levels.append((e_4t2g, '4T2g'))
    
    # 4T1g states: mixing between 4T1g(F) and 4T1g(P)
    # Relative to 4A2g:
    # 4T1g(F): 6Dq - (-12Dq) = 18Dq -> 18x
    # 4T1g(P): 15B + 6Dq - (-12Dq) = 15B + 18Dq -> 15 + 18x
    # Off-diagonal mixing: 4Dq -> 4x
    
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))  # Lower 4T1g (mostly 4T1g(F) character)
    levels.append((eig_4t1g[1], '4T1g'))  # Upper 4T1g (mostly 4T1g(P) character)
    
    # === DOUBLE STATES ===
    # Free ion term energies relative to 4F (in units of B):
    # 2G: 3 + 2*C/B
    # 2H: 3 + 2*C/B (degenerate with 2G)
    # 2P: 15 + 2*C/B
    
    E_2G = 3 + 2*C_over_B  # = 11.188...
    E_2H = 3 + 2*C_over_B  # Same as 2G
    E_2P = 15 + 2*C_over_B  # = 23.188...
    
    # 2Eg matrix (from 2G and 2H)
    # First-order crystal field splitting:
    # 2Eg from 2G: +2Dq relative to 2G barycenter
    # 2Eg from 2H: -3Dq relative to 2H barycenter
    # Mixing term: 2*sqrt(6)*Dq (from group theory coefficients)
    
    H_2eg = np.array([[E_2G + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H - 3*x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g matrix (from 2G and 2H - ignoring 2P which is much higher)
    # 2T1g from 2G: -Dq relative to 2G barycenter
    # 2T1g from 2H: +Dq relative to 2H barycenter
    # Mixing term: approximately 2*Dq
    
    H_2t1g = np.array([[E_2G - x, 2*x], 
                       [2*x, E_2H + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g matrix (from 2G and 2H)
    # 2T2g from 2G: +Dq relative to 2G barycenter
    # 2T2g from 2H: +2Dq relative to 2H barycenter
    # Mixing term: approximately x
    
    H_2t2g = np.array([[E_2G + x, x], 
                       [x, E_2H + 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    # 2A2g from 2F (higher energy)
    # 2F is at approximately 18B + C above 4F
    E_2F = 18 + C_over_B
    # 2A2g from 2F: approximately +6Dq relative to 2F barycenter
    levels.append((E_2F + 6*x, '2A2g'))
    
    # 2T1g from 2P (higher energy, approximately constant)
    levels.append((E_2P, '2T1g'))
    
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
