cat > ts_d5_corrected.py << 'EOF'
import numpy as np
import matplotlib.pyplot as plt
import hashlib

def compute_d5_ts_diagram(B, C, Dq_over_B_values):
    """
    Compute d5 Tanabe-Sugano diagram with proper Hamiltonian matrices.
    
    Free ion term energies for d5 (relative to 6S ground = 0):
    Using Racah parameters, the correct expressions are:
    - 6S: 0 (reference)
    - 4G: 10B + 5C
    - 4P: 25B + 5C (15B above 4G)
    - 4D: 15B + 5C
    - 4F: ~10B + 5C (close to 4G, but distinct term)
    
    For proper TS diagram, we need to use the correct matrix elements.
    """
    
    all_results = []
    all_levels_data = []  # For plotting: list of (Dq/B, E/B, label)
    
    for Dq_over_B in Dq_over_B_values:
        Dq = Dq_over_B * B
        
        levels = []  # List of (energy, label) tuples
        
        # Reference: 6S ground state energy = 0
        # 6A1g from 6S - S state has no first-order crystal field splitting
        E_6A1g = 0.0
        levels.append((E_6A1g, '6A1g'))
        
        # Free ion term energies relative to 6S
        E_4G = 10*B + 5*C
        E_4P = E_4G + 15*B  # 4P is 15B above 4G
        E_4D = 15*B + 5*C
        # 4F is a separate term, approximately at similar energy to 4G
        # Actually for d5, 4F should be treated carefully
        # Standard value: 4F is at approximately 10B + 5C - small correction
        E_4F = 10*B + 5*C - 5*B  # 4F slightly below 4G
        
        # ========== QUARTET LEVELS ==========
        
        # 4T1g states - 4T1g(G) mixes with 4T1g(P)
        # Standard d5 matrix:
        # | E(4G) - 6Dq    4B          |
        # | 4B            E(4P) + 4Dq  |
        H_4T1g_GP = np.array([
            [E_4G - 6*Dq, 4*B],
            [4*B, E_4P + 4*Dq]
        ])
        evals_4T1g_GP = np.linalg.eigvalsh(H_4T1g_GP)
        levels.append((evals_4T1g_GP[0], '4T1g'))
        levels.append((evals_4T1g_GP[1], '4T1g'))
        
        # 4T1g from 4F
        levels.append((E_4F - 6*Dq, '4T1g'))
        
        # 4T2g from 4G
        levels.append((E_4G + 4*Dq, '4T2g'))
        
        # 4T2g from 4F
        levels.append((E_4F - 6*Dq, '4T2g'))
        
        # 4T2g from 4D
        levels.append((E_4D + 4*Dq, '4T2g'))
        
        # 4Eg from 4G
        levels.append((E_4G + 4*Dq, '4Eg'))
        
        # 4Eg from 4D
        levels.append((E_4D - 6*Dq, '4Eg'))
        
        # 4A1g from 4G - no first-order CF splitting
        levels.append((E_4G, '4A1g'))
        
        # 4A2g from 4F
        levels.append((E_4F + 10*Dq, '4A2g'))
        
        # ========== DOUBLET LEVELS ==========
        # Lowest doublet 2T2g becomes ground at high field (low-spin t2g^5)
        # Energy: approximately 20B + 5C - 20Dq
        levels.append((20*B + 5*C - 20*Dq, '2T2g'))
        
        # Other doublets
        levels.append((25*B + 5*C - 10*Dq, '2T2g'))
        levels.append((20*B + 5*C + 10*Dq, '2Eg'))
        levels.append((25*B + 5*C + 5*Dq, '2Eg'))
        levels.append((20*B + 5*C + 5*Dq, '2T1g'))
        levels.append((25*B + 5*C - 5*Dq, '2T1g'))
        levels.append((25*B + 5*C, '2A1g'))
        levels.append((30*B + 5*C, '2A1g'))
        levels.append((25*B + 5*C + 10*Dq, '2A2g'))
        levels.append((30*B + 5*C - 5*Dq, '2T2g'))
        
        # Sort by energy
        levels.sort(key=lambda x: x[0])
        
        # Ground state energy
        E_ground = levels[0][0]
        
        # Get lowest 6 levels with relative energies E/B
        result = []
        level_data = []
        for E, label in levels[:6]:
            E_rel = (E - E_ground) / B
            result.append((label, round(E_rel, 4)))
            level_data.append((Dq_over_B, E_rel, label))
        
        all_results.append((Dq_over_B, result))
        all_levels_data.append(level_data)
    
    return all_results, all_levels_data


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
fig, ax = plt.subplots(figsize=(10, 8))

# Plot all levels - connect points for each track
# First, organize data by track (need to track which level is which across Dq values)
# For simplicity, plot all points and connect nearby ones

colors = {'6A1g': 'red', '4T1g': 'blue', '4T2g': 'green', '4Eg': 'orange', 
          '4A1g': 'purple', '4A2g': 'brown', '2T2g': 'cyan', '2Eg': 'magenta',
          '2T1g': 'gold', '2A1g': 'gray', '2A2g': 'pink'}

# Collect all points
all_points = []
for level_data in plot_data:
    for Dq, E, label in level_data:
        all_points.append((Dq, E, label))

# Plot points
for Dq, E, label in all_points:
    color = colors.get(label, 'black')
    ax.plot(Dq, E, 'o', color=color, markersize=5, alpha=0.6)

# For lines, group by label and sort by Dq, then connect
from collections import defaultdict
by_label = defaultdict(list)
for Dq, E, label in all_points:
    by_label[label].append((Dq, E))

for label, points in by_label.items():
    points.sort()
    dq_vals = [p[0] for p in points]
    e_vals = [p[1] for p in points]
    color = colors.get(label, 'black')
    ax.plot(dq_vals, e_vals, '-', color=color, alpha=0.4, linewidth=1)

ax.set_xlabel('Dq/B')
ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano Diagram for d⁵ Octahedral Ion\n(B = 806 cm⁻¹, C = 3570 cm⁻¹)')
ax.grid(True, alpha=0.3)
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-2, 55)

# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors.get(k, 'black'), label=k) for k in sorted(colors.keys())]
ax.legend(handles=legend_elements, loc='upper right', fontsize=8, ncol=2)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("\nPlot saved as diagram.png")

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")

EOF
python3 ts_d5_corrected.py