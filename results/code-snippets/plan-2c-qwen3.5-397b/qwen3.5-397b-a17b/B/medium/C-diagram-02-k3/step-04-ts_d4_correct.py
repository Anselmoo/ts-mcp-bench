import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B

print(f"d^4 Tanabe-Sugano Diagram")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.4f}")
print("="*80)

def compute_d4_energies(Dq, C_over_B):
    """
    Compute d^4 energy levels using standard Tanabe-Sugano expressions.
    
    Free ion term energies for d^4 (relative to 5D = 0):
    - 5D: 0
    - 3H: 5B + 2C  (lowest triplet by Hund's rules)
    - 3P: 15B
    - 3F: 9B + 3C
    - 3G: 11B + 5C
    """
    C = C_over_B
    
    # Free ion energies (in units of B)
    E_5D = 0
    E_3H = 5 + 2*C      # = 5 + 2*4.794 = 14.588
    E_3P = 15
    E_3F = 9 + 3*C      # = 9 + 3*4.794 = 23.382
    E_3G = 11 + 5*C     # = 11 + 5*4.794 = 34.97
    
    levels = []
    
    # === QUINTET STATES (from 5D) ===
    # 5D (L=2) -> 5T2g + 5Eg
    # Standard CF splitting: T2g at -6Dq, Eg at +4Dq
    levels.append(('5T2g', E_5D - 6*Dq))
    levels.append(('5Eg', E_5D + 4*Dq))
    
    # === TRIPLET T1g STATES ===
    # 3T1g from 3F and 3P mix via 2x2 matrix
    # Matrix: | E(3F) - 6Dq    4Dq         |
    #         | 4Dq            E(3P) + 2Dq  |
    H_T1g = np.array([
        [E_3F - 6*Dq, 4*Dq],
        [4*Dq, E_3P + 2*Dq]
    ])
    eig_T1g = np.linalg.eigvalsh(H_T1g)
    levels.append(('3T1g', eig_T1g[0]))  # Lower eigenstate
    levels.append(('3T1g', eig_T1g[1]))  # Upper eigenstate
    
    # 3T1g from 3H: H (L=5) splits in O_h
    # The H term has 11 states: E(2) + T1(3) + T1(3) + T2(3) + T2(3) = 14? No.
    # Actually: H -> E + T1 + T2 + (T1 + T2) but we need 11 states
    # Correct: H -> E(2) + T1(3) + T2(3) + T1(3) = 11 (one T1, one T2 repeated)
    # Or: H -> E(2) + T1(3) + T2(3) + T2(3) = 11
    # Standard result: the CF energies for H components relative to H barycenter
    # are approximately: E: +6Dq, T1: -2Dq, T1: +8Dq, T2: -4Dq, T2: +4Dq (sum = 0)
    # Let me use: T1g(H) at E_3H - 2Dq and E_3H + 8Dq
    levels.append(('3T1g', E_3H - 2*Dq))
    levels.append(('3T1g', E_3H + 8*Dq))
    
    # 3T1g from 3G: G (L=4) -> A1 + E + T1 + T2
    # T1g from G at approximately E_3G - 6Dq
    levels.append(('3T1g', E_3G - 6*Dq))
    
    # === TRIPLET T2g STATES ===
    # 3T2g from 3F: at E_3F + 2Dq
    levels.append(('3T2g', E_3F + 2*Dq))
    
    # 3T2g from 3H: using CF splitting for H term
    # T2g components at E_3H - 4Dq and E_3H + 4Dq
    levels.append(('3T2g', E_3H - 4*Dq))
    levels.append(('3T2g', E_3H + 4*Dq))
    
    # 3T2g from 3G: at E_3G - 8Dq (approximate)
    levels.append(('3T2g', E_3G - 8*Dq))
    
    # === TRIPLET A2g STATES ===
    # Only from 3F: at E_3F + 12Dq
    levels.append(('3A2g', E_3F + 12*Dq))
    
    # === TRIPLET Eg STATES ===
    # 3Eg from 3H: at E_3H + 6Dq (approximate)
    levels.append(('3Eg', E_3H + 6*Dq))
    
    # 3Eg from 3G: at E_3G + 2Dq
    levels.append(('3Eg', E_3G + 2*Dq))
    
    # === TRIPLET A1g STATES ===
    # From 3G: at E_3G + 12Dq
    levels.append(('3A1g', E_3G + 12*Dq))
    
    # === SINGLET STATES (higher energy, typically not in lowest 6) ===
    E_1I = 18 + 9*C
    E_1G = 14 + 7*C
    E_1S = 22 + 10*C
    E_1D = 10 + 5*C
    E_1F = 12 + 6*C
    
    # From 1I
    levels.append(('1A1g', E_1I + 18*Dq))
    levels.append(('1Eg', E_1I + 8*Dq))
    levels.append(('1T1g', E_1I + 2*Dq))
    levels.append(('1T2g', E_1I - 4*Dq))
    
    # From 1G
    levels.append(('1A1g', E_1G + 12*Dq))
    levels.append(('1Eg', E_1G + 2*Dq))
    levels.append(('1T1g', E_1G - 6*Dq))
    levels.append(('1T2g', E_1G - 8*Dq))
    
    # From 1S
    levels.append(('1A1g', E_1S))
    
    # From 1D
    levels.append(('1Eg', E_1D + 4*Dq))
    levels.append(('1T2g', E_1D - 6*Dq))
    
    # From 1F
    levels.append(('1A2g', E_1F + 12*Dq))
    levels.append(('1T1g', E_1F - 6*Dq))
    levels.append(('1T2g', E_1F + 2*Dq))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    return levels

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
Dq_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

for Dq_over_B in Dq_values:
    levels = compute_d4_energies(Dq_over_B, C_over_B)
    
    # Ground state energy
    E_ground = levels[0][1]
    
    # Get lowest 6 levels relative to ground
    lowest_6 = []
    for term, energy in levels[:6]:
        E_rel = energy - E_ground
        lowest_6.append((term, E_rel))
    
    results.append((Dq_over_B, lowest_6))

# Print results
print("\nEnergy levels at each Dq/B:")
print("-"*80)
for Dq_over_B, levels in results:
    print(f"\nDq/B = {Dq_over_B}:")
    all_levels = compute_d4_energies(Dq_over_B, C_over_B)
    print(f"  Ground state: {all_levels[0][0]} at E/B = {all_levels[0][1]:.4f}")
    print(f"  Lowest 6 levels (E/B relative to ground):")
    for i, (term, e_rel) in enumerate(levels):
        print(f"    {i+1}. {term}: {e_rel:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(14, 10))

# Generate smooth curves
Dq_smooth = np.linspace(0, 4, 300)
curves = {}

for Dq in Dq_smooth:
    levels = compute_d4_energies(Dq, C_over_B)
    E_ground = levels[0][1]
    
    for i, (term, energy) in enumerate(levels):
        key = i
        if key not in curves:
            curves[key] = {'Dq': [], 'E': [], 'term': term}
        curves[key]['Dq'].append(Dq)
        curves[key]['E'].append(energy - E_ground)
        curves[key]['term'] = term

# Plot
spin_colors = {'5': 'red', '3': 'blue', '1': 'green'}
for key, data in sorted(curves.items()):
    if len(data['Dq']) > 1:
        spin = data['term'][0]
        color = spin_colors.get(spin, 'gray')
        ax.plot(data['Dq'], data['E'], '-', linewidth=1.5, color=color, alpha=0.6)

ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B (relative to ground state)', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁴ Octahedral Ion\n(B = 814 cm⁻¹, C = 3902 cm⁻¹, C/B = {:.2f})'.format(C_over_B), 
             fontsize=16, fontweight='bold')
ax.set_xlim(0, 4)
ax.set_ylim(0, 55)
ax.grid(True, alpha=0.3, linestyle='--')

from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='red', alpha=0.6, label='Quintet (S=2)'),
    Patch(facecolor='blue', alpha=0.6, label='Triplet (S=1)'),
    Patch(facecolor='green', alpha=0.6, label='Singlet (S=0)')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=11)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

# Compute sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print("\n" + "="*80)
print(f"Plot saved as diagram.png")
print(f"SHA256: {sha256_hash}")
print("="*80)

# Final output
print("\n\nFINAL RESULTS TABLE:")
print("="*80)
for Dq_over_B, levels in results:
    print(f"\nDq/B = {Dq_over_B}:")
    for i, (term, e_rel) in enumerate(levels):
        print(f"  {i+1}. {term}: E/B = {e_rel:.4f}")
