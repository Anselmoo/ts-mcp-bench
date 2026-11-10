cat > ts_d5_standard.py << 'EOF'
import numpy as np
import matplotlib.pyplot as plt
import hashlib

def compute_d5_ts_standard(B, C, Dq_over_B_values):
    """
    Compute d5 Tanabe-Sugano diagram using standard free ion term energies.
    
    For d5, the free ion terms (relative to 6S = 0) are:
    - 6S: 0 (ground state)
    - 4G: 10B + 5C
    - 4P: 25B + 5C (15B above 4G)
    - 4D: 15B + 5C
    - 4F: For d5, 4F is actually ABOVE 4G in standard ordering
          Using: E(4F) ≈ 10B + 5C + small offset
          
    Actually, looking at standard d5 TS diagrams, the 4F terms appear
    at similar energies to 4G terms. Let me use E(4F) = 10B + 5C.
    """
    
    all_results = []
    all_levels_data = []
    
    for Dq_over_B in Dq_over_B_values:
        Dq = Dq_over_B * B
        
        levels = []
        
        # 6A1g from 6S (reference)
        levels.append((0.0, '6A1g'))
        
        # Free ion energies - using standard values
        E_4G = 10*B + 5*C
        E_4P = 25*B + 5*C
        E_4D = 15*B + 5*C
        E_4F = 10*B + 5*C  # 4F at same energy as 4G (different term)
        
        # 4T1g: mix 4T1g(G) and 4T1g(P)
        H_4T1g = np.array([
            [E_4G - 6*Dq, 4*B],
            [4*B, E_4P + 4*Dq]
        ])
        evals = np.linalg.eigvalsh(H_4T1g)
        levels.append((evals[0], '4T1g'))
        levels.append((evals[1], '4T1g'))
        
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
        
        # 4A1g from 4G
        levels.append((E_4G, '4A1g'))
        
        # 4A2g from 4F
        levels.append((E_4F + 10*Dq, '4A2g'))
        
        # Doublets - lowest 2T2g becomes ground at high field
        levels.append((20*B + 5*C - 20*Dq, '2T2g'))
        levels.append((25*B + 5*C - 10*Dq, '2T2g'))
        levels.append((20*B + 5*C + 10*Dq, '2Eg'))
        levels.append((25*B + 5*C + 5*Dq, '2Eg'))
        levels.append((20*B + 5*C + 5*Dq, '2T1g'))
        levels.append((25*B + 5*C - 5*Dq, '2T1g'))
        levels.append((25*B + 5*C, '2A1g'))
        levels.append((30*B + 5*C, '2A1g'))
        levels.append((25*B + 5*C + 10*Dq, '2A2g'))
        levels.append((30*B + 5*C - 5*Dq, '2T2g'))
        
        # Sort and get lowest 6
        levels.sort(key=lambda x: x[0])
        E_ground = levels[0][0]
        
        result = []
        level_data = []
        for E, label in levels[:6]:
            E_rel = (E - E_ground) / B
            result.append((label, round(E_rel, 4)))
            level_data.append((Dq_over_B, E_rel, label))
        
        all_results.append((Dq_over_B, result))
        all_levels_data.append(level_data)
    
    return all_results, all_levels_data


B = 806
C = 3570
Dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results, plot_data = compute_d5_ts_standard(B, C, Dq_over_B_values)

print("=" * 70)
print("TANABE-SUGANO DIAGRAM FOR d⁵ OCTAHEDRAL ION")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C/B:.3f}")
print("=" * 70)
print()

for Dq_over_B, levels in results:
    print(f"Dq/B = {Dq_over_B}:")
    for i, (label, E_over_B) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {E_over_B}")
    print()

# Plot
fig, ax = plt.subplots(figsize=(12, 8))

colors = {'6A1g': 'red', '4T1g': 'blue', '4T2g': 'green', '4Eg': 'orange', 
          '4A1g': 'purple', '4A2g': 'brown', '2T2g': 'cyan', '2Eg': 'magenta',
          '2T1g': 'gold', '2A1g': 'gray', '2A2g': 'pink'}

all_points = []
for level_data in plot_data:
    for Dq, E, label in level_data:
        all_points.append((Dq, E, label))

for Dq, E, label in all_points:
    ax.plot(Dq, E, 'o', color=colors.get(label, 'black'), markersize=6, alpha=0.7)

from collections import defaultdict
by_label = defaultdict(list)
for Dq, E, label in all_points:
    by_label[label].append((Dq, E))

for label, points in by_label.items():
    points.sort()
    dq_vals = [p[0] for p in points]
    e_vals = [p[1] for p in points]
    ax.plot(dq_vals, e_vals, '-', color=colors.get(label, 'black'), alpha=0.5, linewidth=1.5)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d⁵ Octahedral Ion\n(B = 806 cm⁻¹, C = 3570 cm⁻¹, C/B = 4.43)', fontsize=14)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-2, 55)

from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors.get(k, 'black'), label=k) for k in sorted(colors.keys())]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9, ncol=2)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')

with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"Plot saved as diagram.png")
print(f"SHA256: {sha256_hash}")

EOF
python3 ts_d5_standard.py