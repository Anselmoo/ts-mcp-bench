import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json

# Racah parameters
B = 551.0  # cm^-1
C = 2511.0  # cm^-1
C_over_B = C / B  # 4.557168784

# For d6 octahedral Tanabe-Sugano diagram
# Based on standard references (Tanabe & Sugano 1954, Figgis & Hitchman)

def d6_TS_energies(Dq_over_B, C_over_B=C_over_B):
    """
    Calculate d6 octahedral Tanabe-Sugano energies.
    
    Free ion terms for d6 (relative to 5D ground):
    - 5D: 0 (ground)
    - 3H: ~9B (actually depends on Racah parameters more precisely)
    - 3F: 15B
    - 3P: 15B + 7C (mixes with 3T1g from 3F)
    - 1I, 1G, 1D, 1S: various singlets at higher energy
    - 3G: also contributes triplets
    
    Using standard weak-field energies from crystal field theory.
    """
    DqB = Dq_over_B
    
    levels = []
    
    # ============== QUINTET STATES (S=2) ==============
    # From 5D term (ground free-ion term)
    # In octahedral field: 5T2g + 5Eg
    # Relative to 5D barycenter: 5T2g at -4Dq, 5Eg at +6Dq
    levels.append((-4 * DqB, "5T2g"))
    levels.append((6 * DqB, "5Eg"))
    
    # ============== TRIPLET STATES (S=1) ==============
    
    # From 3F term (at 15B above 5D):
    # In octahedral field: 3A2g + 3T2g + 3T1g
    E_3F = 15.0
    levels.append((E_3F - 6 * DqB, "3T1g(F)"))  # Will mix with 3T1g(P)
    levels.append((E_3F - 1 * DqB, "3T2g(F)"))
    levels.append((E_3F + 9 * DqB, "3A2g(F)"))
    
    # From 3P term (at 15B + 7C above 5D):
    # Only gives 3T1g which mixes with 3T1g from 3F
    E_3P = 15.0 + 7.0 * C_over_B
    
    # Diagonalize 2x2 matrix for the two 3T1g states
    # Off-diagonal element: 4Dq (standard result for d6)
    H_3T1g = np.array([
        [E_3F - 6 * DqB, 4 * DqB],
        [4 * DqB, E_3P]
    ])
    eig_3T1g = np.linalg.eigvalsh(H_3T1g)
    # Remove the 3T1g(F) we already added, replace with eigenvalues
    levels = [l for l in levels if l[1] != "3T1g(F)"]
    levels.append((eig_3T1g[0], "3T1g(F)"))
    levels.append((eig_3T1g[1], "3T1g(P)"))
    
    # From 3H term (at ~9B above 5D for d6):
    # 3H (L=5) splits in Oh into: 3T1g + 3T2g + 3A2g + 3T1g + 3T2g
    # Using standard weak-field splitting for H term:
    E_3H = 9.0
    
    # The splitting of H (L=5) in octahedral field follows specific pattern
    # Using energies from standard references:
    # The five components have Dq dependence:
    # Based on Griffith's tables for L=5 in O symmetry:
    levels.append((E_3H - 10 * DqB, "3T1g(H)"))  # Lower 3T1g from 3H
    levels.append((E_3H - 5 * DqB, "3T2g(H)"))   # Lower 3T2g from 3H
    levels.append((E_3H + 5 * DqB, "3A2g(H)"))   # 3A2g from 3H
    levels.append((E_3H + 10 * DqB, "3T1g(H2)")) # Upper 3T1g from 3H
    levels.append((E_3H + 15 * DqB, "3T2g(H2)")) # Upper 3T2g from 3H
    
    # From 3G term (at ~12B + 5C above 5D):
    # 3G (L=4) splits into: 3A1g + 3Eg + 3T1g + 3T2g
    E_3G = 12.0 + 5.0 * C_over_B
    levels.append((E_3G - 4 * DqB, "3A1g(G)"))
    levels.append((E_3G + 1 * DqB, "3Eg(G)"))
    levels.append((E_3G + 6 * DqB, "3T1g(G)"))
    levels.append((E_3G + 11 * DqB, "3T2g(G)"))
    
    # ============== SINGLET STATES (S=0) ==============
    
    # From 1I term (L=6, at ~17B + 5C above 5D):
    # 1I splits into: 1A1g + 1Eg + 1T1g + 1T2g + 1Eg + 1T2g
    E_1I = 17.0 + 5.0 * C_over_B
    
    # Using standard L=6 splitting in octahedral field:
    levels.append((E_1I - 24 * DqB, "1A1g(I)"))  # Drops steeply
    levels.append((E_1I - 14 * DqB, "1T1g(I)"))
    levels.append((E_1I - 9 * DqB, "1T2g(I)"))
    levels.append((E_1I - 4 * DqB, "1Eg(I)"))
    levels.append((E_1I + 11 * DqB, "1Eg(I2)"))
    levels.append((E_1I + 16 * DqB, "1T2g(I2)"))
    
    # From 1G term (L=4, at ~12B + 5C above 5D):
    # 1G splits into: 1A1g + 1Eg + 1T1g + 1T2g
    E_1G = 12.0 + 5.0 * C_over_B
    levels.append((E_1G - 4 * DqB, "1A1g(G)"))
    levels.append((E_1G + 1 * DqB, "1Eg(G)"))
    levels.append((E_1G + 6 * DqB, "1T1g(G)"))
    levels.append((E_1G + 11 * DqB, "1T2g(G)"))
    
    # From 1D term (L=2, at ~10B + 5C above 5D):
    # 1D splits into: 1Eg + 1T2g
    E_1D = 10.0 + 5.0 * C_over_B
    levels.append((E_1D - 6 * DqB, "1Eg(D)"))
    levels.append((E_1D + 4 * DqB, "1T2g(D)"))
    
    # From 1S term (L=0, at ~22B + 7C above 5D):
    # 1S gives only 1A1g with no Dq dependence
    E_1S = 22.0 + 7.0 * C_over_B
    levels.append((E_1S, "1A1g(S)"))
    
    # From 1F term (L=3, at higher energy):
    # 1F splits into: 1A2g + 1T1g + 1T2g
    E_1F = 15.0 + 7.0 * C_over_B  # Approximate
    levels.append((E_1F - 6 * DqB, "1A2g(F)"))
    levels.append((E_1F + 2 * DqB, "1T1g(F)"))
    levels.append((E_1F + 8 * DqB, "1T2g(F)"))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Normalize so ground state is at 0
    if levels:
        E_ground = levels[0][0]
        levels = [(E - E_ground, label) for E, label in levels]
    
    return levels


# Calculate for each Dq/B value
Dq_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d6 Octahedral Ion")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.4f}")
print("=" * 70)

all_results = []

for DqB in Dq_B_values:
    levels = d6_TS_energies(DqB)
    
    print(f"\nDq/B = {DqB:.1f}:")
    print("  #   Term            E/B")
    print("  --  --------------  --------")
    for i, (E, label) in enumerate(levels[:12]):
        print(f"  {i+1:2d}   {label:14s}  {E:8.3f}")
    
    # Store lowest 6 levels
    lowest_6 = [(label, E) for E, label in levels[:6]]
    all_results.append({
        'Dq_over_B': DqB,
        'levels': lowest_6
    })

# Save results
with open('d6_ts_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)

print("\n" + "=" * 70)
print("Summary - Lowest 6 levels at each Dq/B:")
for res in all_results:
    print(f"\nDq/B = {res['Dq_over_B']:.1f}:")
    for label, E in res['levels']:
        print(f"  {label}: E/B = {E:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(10, 8))

# Collect all levels for plotting
plot_data = {DqB: d6_TS_energies(DqB) for DqB in np.linspace(0, 4, 100)}

# Plot all levels up to E/B = 50
colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

# Group by term type for coloring
term_colors = {}
color_idx = 0

for DqB in np.linspace(0, 4, 100):
    levels = d6_TS_energies(DqB)
    for E, label in levels:
        if E < 50:  # Only plot lower levels
            # Extract base term name for coloring
            base_term = label.split('(')[0] if '(' in label else label
            if base_term not in term_colors:
                term_colors[base_term] = colors[color_idx % len(colors)]
                color_idx += 1
            
            ax.plot(DqB, E, 'o', color=term_colors[base_term], markersize=2, alpha=0.3)

# Also plot continuous lines for the lowest several levels
DqB_fine = np.linspace(0, 4, 200)
for level_idx in range(15):
    energies = []
    for DqB in DqB_fine:
        levels = d6_TS_energies(DqB)
        if level_idx < len(levels):
            energies.append(levels[level_idx][0])
        else:
            energies.append(np.nan)
    ax.plot(DqB_fine, energies, 'k-', linewidth=0.5, alpha=0.5)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d⁶ Octahedral Ion\n(B = 551 cm⁻¹, C = 2511 cm⁻¹, C/B = 4.56)', fontsize=14)
ax.set_xlim(0, 4)
ax.set_ylim(0, 50)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("\nPlot saved to diagram.png")

# Print final results in required format
print("\n" + "=" * 70)
print("FINAL RESULTS - Lowest 6 levels:")
print("=" * 70)
for res in all_results:
    print(f"\nDq/B = {res['Dq_over_B']}:")
    for label, E in res['levels']:
        print(f"  {label}: E/B = {E:.6f}")
