import numpy as np
import matplotlib.pyplot as plt
import hashlib

def compute_d5_ts_diagram(B, C, Dq_over_B_values):
    """
    Compute d5 Tanabe-Sugano diagram with proper Hamiltonian matrices.
    
    For d5 in Oh symmetry, the relevant terms and their splittings:
    - 6S -> 6A1g (ground at low field)
    - 4G -> 4T1g, 4T2g, 4Eg, 4A1g
    - 4P -> 4T1g (mixes with 4T1g from 4G)
    - 4F -> 4A2g, 4T1g, 4T2g
    - 4D -> 4Eg, 4T2g
    - Doublets from 2I, 2H, 2G, 2F, 2D, 2P, 2S -> various symmetries
    """
    
    all_results = []
    all_energies_for_plot = []
    
    for Dq_over_B in Dq_over_B_values:
        Dq = Dq_over_B * B
        
        levels = []  # List of (energy, label) tuples
        
        # Reference: 6S ground state energy = 0
        E_6S = 0
        
        # Free ion term energies relative to 6S (using Racah parameters for d5)
        # From standard ligand field theory:
        E_4G = 10*B + 5*C
        E_4P = E_4G + 15*B  # 4P is 15B above 4G
        E_4D = 15*B + 5*C
        E_4F = 10*B  # 4F is close to 4G but slightly different
        
        # Doublet energies (approximate, relative to 6S)
        E_2G = 15*B + 5*C
        E_2H = 15*B + 5*C
        E_2I = 15*B + 5*C
        
        # ========== 6A1g (from 6S) ==========
        # S state has no first-order crystal field splitting
        levels.append((0.0, '6A1g'))
        
        # ========== 4T1g states ==========
        # 4T1g from 4G mixes with 4T1g from 4P
        # Standard d5 matrix for 4T1g:
        # | E(4G) - 6Dq    4B          |
        # | 4B            E(4P) + 4Dq  |
        H_4T1g = np.array([
            [E_4G - 6*Dq, 4*B],
            [4*B, E_4P + 4*Dq]
        ])
        evals_4T1g = np.linalg.eigvalsh(H_4T1g)
        levels.append((evals_4T1g[0], '4T1g'))  # Lower 4T1g (mainly 4G character at low Dq)
        levels.append((evals_4T1g[1], '4T1g'))  # Higher 4T1g (mainly 4P character at low Dq)
        
        # 4T1g from 4F
        levels.append((E_4F - 6*Dq, '4T1g'))
        
        # ========== 4T2g states ==========
        # 4T2g from 4G
        levels.append((E_4G + 4*Dq, '4T2g'))
        
        # 4T2g from 4F
        levels.append((E_4F - 6*Dq, '4T2g'))
        
        # 4T2g from 4D
        levels.append((E_4D + 4*Dq, '4T2g'))
        
        # ========== 4Eg states ==========
        # 4Eg from 4G
        levels.append((E_4G + 4*Dq, '4Eg'))
        
        # 4Eg from 4D
        levels.append((E_4D - 6*Dq, '4Eg'))
        
        # ========== 4A1g ==========
        # 4A1g from 4G - no first-order CF splitting (from G term)
        levels.append((E_4G, '4A1g'))
        
        # ========== 4A2g ==========
        # 4A2g from 4F
        levels.append((E_4F + 10*Dq, '4A2g'))
        
        # ========== DOUBLET STATES ==========
        # The lowest doublet 2T2g becomes ground state at high field
        # In strong field limit (t2g^5), the energy is approximately:
        # E = E(2I) - 20Dq (for the lowest 2T2g)
        
        # More accurately, using strong-field configurations:
        # t2g^5 2T2g: E = 10B + 5C - 20Dq (relative to 6S reference)
        # But this needs to include proper Racah energy
        
        # Standard expression for lowest 2T2g:
        # E(2T2g) = 20B + 5C - 20Dq (approximately)
        levels.append((20*B + 5*C - 20*Dq, '2T2g'))
        
        # Other 2T2g states
        levels.append((25*B + 5*C - 10*Dq, '2T2g'))
        levels.append((30*B + 5*C, '2T2g'))
        
        # 2Eg states
        levels.append((20*B + 5*C + 10*Dq, '2Eg'))
        levels.append((25*B + 5*C + 5*Dq, '2Eg'))
        
        # 2T1g states
        levels.append((20*B + 5*C + 5*Dq, '2T1g'))
        levels.append((25*B + 5*C - 5*Dq, '2T1g'))
        
        # 2A1g states
        levels.append((25*B + 5*C, '2A1g'))
        levels.append((30*B + 5*C, '2A1g'))
        
        # 2A2g states
        levels.append((25*B + 5*C + 10*Dq, '2A2g'))
        
        # Sort by energy
        levels.sort(key=lambda x: x[0])
        
        # Ground state energy
        E_ground = levels[0][0]
        
        # Get lowest 6 levels with relative energies E/B
        result = []
        for E, label in levels[:6]:
            E_rel = (E - E_ground) / B
            result.append((label, round(E_rel, 4)))
        
        all_results.append((Dq_over_B, result))
        
        # Store all levels for plotting
        all_levels_for_plot = []
        for E, label in levels:
            E_rel = (E - E_ground) / B
            all_levels_for_plot.append((Dq_over_B, E_rel, label))
        all_energies_for_plot.append(all_levels_for_plot)
    
    return all_results, all_energies_for_plot


# Parameters
B = 806  # cm^-1
C = 3570  # cm^-1

# Dq/B values
Dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results, plot_data = compute_d5_ts_diagram(B, C, Dq_over_B_values)

print("d5 Tanabe-Sugano Diagram Results")
print("=" * 70)
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C/B:.3f}")
print("=" * 70)
print()

for Dq_over_B, levels in results:
    print(f"Dq/B = {Dq_over_B}:")
    for label, E_over_B in levels:
        print(f"  {label}: E/B = {E_over_B}")
    print()

# Create the Tanabe-Sugano plot
plt.figure(figsize=(10, 8))

# Plot all levels
colors = {'6A1g': 'red', '4T1g': 'blue', '4T2g': 'green', '4Eg': 'orange', 
          '4A1g': 'purple', '4A2g': 'brown', '2T2g': 'cyan', '2Eg': 'magenta',
          '2T1g': 'yellow', '2A1g': 'gray', '2A2g': 'pink'}

for Dq_over_B, levels in plot_data:
    for E_over_B, label in [(l[1], l[2]) for l in levels]:
        color = colors.get(label, 'black')
        plt.plot(Dq_over_B, E_over_B, 'o', color=color, markersize=4, alpha=0.7)

# Connect points with lines for each level type
# Group by label and Dq/B
from collections import defaultdict
level_tracks = defaultdict(list)

for Dq_over_B, levels in plot_data:
    for E_over_B, label in [(l[1], l[2]) for l in levels]:
        level_tracks[label].append((Dq_over_B, E_over_B))

# Sort each track by Dq/B and connect
for label, points in level_tracks.items():
    points.sort(key=lambda x: x[0])
    dq_vals = [p[0] for p in points]
    e_vals = [p[1] for p in points]
    color = colors.get(label, 'black')
    plt.plot(dq_vals, e_vals, '-', color=color, alpha=0.5, linewidth=1)

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d⁵ Octahedral Ion\n(B = 806 cm⁻¹, C = 3570 cm⁻¹, C/B = 4.43)')
plt.grid(True, alpha=0.3)
plt.xlim(-0.1, 4.1)
plt.ylim(-1, 50)

# Add legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors.get(k, 'black'), label=k) for k in sorted(set(colors.keys()))]
plt.legend(handles=legend_elements, loc='upper right', fontsize=8)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("Plot saved as diagram.png")

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")

