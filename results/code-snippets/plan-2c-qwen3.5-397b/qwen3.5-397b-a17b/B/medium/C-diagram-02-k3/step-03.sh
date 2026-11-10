cat > ts_d4_final.py << 'EOF'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B

print(f"d^4 Tanabe-Sugano Diagram")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.4f}")
print("="*80)

def compute_d4_energies(Dq_over_B, C_over_B):
    """
    Compute d^4 energy levels in octahedral field.
    
    Free ion term energies for d^4 (relative to 5D = 0):
    Using standard Racah parameterization (Griffith, Figgis):
    - 5D: 0
    - 3H: 5B + 2C
    - 3P: 15B  
    - 3F: 9B + 3C
    - 3G: 11B + 5C
    - 1I: 18B + 9C
    - 1G: 14B + 7C
    - 1S: 22B + 10C
    - 1D: 10B + 5C
    - 1F: 12B + 6C
    """
    Dq = Dq_over_B
    C = C_over_B
    
    # Free ion energies (in units of B)
    E_5D = 0
    E_3H = 5 + 2*C
    E_3P = 15
    E_3F = 9 + 3*C
    E_3G = 11 + 5*C
    E_1I = 18 + 9*C
    E_1G = 14 + 7*C
    E_1S = 22 + 10*C
    E_1D = 10 + 5*C
    E_1F = 12 + 6*C
    
    levels = []
    
    # === QUINTET STATES (from 5D only) ===
    # 5D (L=2) -> 5T2g + 5Eg in O_h
    # CF splitting: T2g at -6Dq, Eg at +4Dq relative to 5D barycenter
    levels.append(('5T2g', E_5D - 6*Dq))
    levels.append(('5Eg', E_5D + 4*Dq))
    
    # === TRIPLET T1g STATES ===
    # Sources: 3P (L=1), 3F (L=3), 3H (L=5), 3G (L=4)
    # 3T1g(F) and 3T1g(P) mix via 2x2 matrix
    # 3T1g(H) and 3T1g(G) are separate (higher energy, weak mixing)
    
    # 3T1g(F-P) mixing matrix (standard result from Figgis):
    # | E(3F) - 6Dq    4Dq         |
    # | 4Dq            E(3P) + 2Dq  |
    H_T1g_FP = np.array([
        [E_3F - 6*Dq, 4*Dq],
        [4*Dq, E_3P + 2*Dq]
    ])
    eig_T1g_FP = np.linalg.eigvalsh(H_T1g_FP)
    levels.append(('3T1g', eig_T1g_FP[0]))  # Lower (F-character at low field)
    levels.append(('3T1g', eig_T1g_FP[1]))  # Upper (P-character)
    
    # 3T1g from 3H: H (L=5) -> E + T1 + T2 + T1 + T2 in O_h
    # The T1g components from H have various CF energies
    # Using approximate values from group theory
    levels.append(('3T1g', E_3H - 4*Dq))  # One T1g component from H
    levels.append(('3T1g', E_3H + 6*Dq))  # Another T1g component from H
    
    # 3T1g from 3G: G (L=4) -> A1 + E + T1 + T2 in O_h
    # T1g from G at approximately -6Dq relative to G barycenter
    levels.append(('3T1g', E_3G - 6*Dq))
    
    # === TRIPLET T2g STATES ===
    # Sources: 3F, 3H, 3G
    
    # 3T2g from 3F: at E(3F) + 2Dq
    levels.append(('3T2g', E_3F + 2*Dq))
    
    # 3T2g from 3H: multiple components
    levels.append(('3T2g', E_3H - 6*Dq))  # One component
    levels.append(('3T2g', E_3H + 8*Dq))  # Another component
    
    # 3T2g from 3G
    levels.append(('3T2g', E_3G - 8*Dq))
    
    # === TRIPLET A2g STATES ===
    # Only from 3F: at E(3F) + 12Dq
    levels.append(('3A2g', E_3F + 12*Dq))
    
    # === TRIPLET Eg STATES ===
    # Sources: 3H, 3G
    
    # 3Eg from 3H
    levels.append(('3Eg', E_3H))  # Approximately at barycenter
    levels.append(('3Eg', E_3H + 10*Dq))  # Another component
    
    # 3Eg from 3G
    levels.append(('3Eg', E_3G + 2*Dq))
    
    # === TRIPLET A1g STATES ===
    # From 3G only
    levels.append(('3A1g', E_3G + 12*Dq))
    
    # === SINGLET STATES ===
    # From 1I (L=6): A1 + A2 + E + T1 + T2 + T1 + T2
    levels.append(('1A1g', E_1I + 18*Dq))
    levels.append(('1A2g', E_1I + 12*Dq))
    levels.append(('1Eg', E_1I + 8*Dq))
    levels.append(('1Eg', E_1I - 2*Dq))
    levels.append(('1T1g', E_1I + 4*Dq))
    levels.append(('1T1g', E_1I - 6*Dq))
    levels.append(('1T2g', E_1I + 2*Dq))
    levels.append(('1T2g', E_1I - 8*Dq))
    
    # From 1G (L=4): A1 + E + T1 + T2
    levels.append(('1A1g', E_1G + 12*Dq))
    levels.append(('1Eg', E_1G + 2*Dq))
    levels.append(('1T1g', E_1G - 6*Dq))
    levels.append(('1T2g', E_1G - 8*Dq))
    
    # From 1S (L=0): only A1, no CF splitting
    levels.append(('1A1g', E_1S))
    
    # From 1D (L=2): E + T2
    levels.append(('1Eg', E_1D + 4*Dq))
    levels.append(('1T2g', E_1D - 6*Dq))
    
    # From 1F (L=3): A2 + T1 + T2
    levels.append(('1A2g', E_1F + 12*Dq))
    levels.append(('1T1g', E_1F - 6*Dq))
    levels.append(('1T2g', E_1F + 2*Dq))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    return levels

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
Dq_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

print("\nEnergy levels at each Dq/B:")
print("-"*80)

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
    
    print(f"\nDq/B = {Dq_over_B}:")
    print(f"  Ground state: {levels[0][0]} at E/B = {levels[0][1]:.4f}")
    print(f"  Lowest 6 levels (E/B relative to ground):")
    for i, (term, e_rel) in enumerate(lowest_6):
        print(f"    {i+1}. {term}: {e_rel:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(14, 10))

# Generate smooth curves for plotting
Dq_smooth = np.linspace(0, 4, 300)
curves = {}

for Dq in Dq_smooth:
    levels = compute_d4_energies(Dq, C_over_B)
    E_ground = levels[0][1]
    
    for i, (term, energy) in enumerate(levels):
        # Track curves by index to maintain continuity
        key = i
        if key not in curves:
            curves[key] = {'Dq': [], 'E': [], 'term': term}
        curves[key]['Dq'].append(Dq)
        curves[key]['E'].append(energy - E_ground)
        curves[key]['term'] = term

# Plot with different colors for different spin multiplicities
spin_colors = {'5': 'red', '3': 'blue', '1': 'green'}

for key, data in sorted(curves.items()):
    if len(data['Dq']) > 1:
        spin = data['term'][0]  # First char is multiplicity
        color = spin_colors.get(spin, 'gray')
        ax.plot(data['Dq'], data['E'], '-', linewidth=1.5, color=color, alpha=0.6)

# Add labels for key states at Dq/B = 0 and Dq/B = 4
ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B (relative to ground state)', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁴ Octahedral Ion\n(B = 814 cm⁻¹, C = 3902 cm⁻¹, C/B = {:.2f})'.format(C_over_B), 
             fontsize=16, fontweight='bold')
ax.set_xlim(0, 4)
ax.set_ylim(0, 55)
ax.grid(True, alpha=0.3, linestyle='--')

# Add legend patches
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

print("\n" + "="*80)
print("Plot saved as diagram.png")

# Compute sha256
import hashlib
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"SHA256: {sha256_hash}")
print("="*80)

# Final formatted output for structured response
print("\n\nFINAL RESULTS:")
print("="*80)
output_data = []
for Dq_over_B, levels in results:
    print(f"\nDq/B = {Dq_over_B}:")
    point_data = {'Dq_over_B': Dq_over_B, 'levels': []}
    for i, (term, e_rel) in enumerate(levels):
        print(f"  {i+1}. {term}: E/B = {e_rel:.4f}")
        point_data['levels'].append({'term': term, 'E_over_B': e_rel})
    output_data.append(point_data)

# Save as JSON for reference
import json
with open('ts_results.json', 'w') as f:
    json.dump(output_data, f, indent=2)

print("\nResults also saved to ts_results.json")
EOF
python3 ts_d4_final.py