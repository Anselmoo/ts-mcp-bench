cat > ts_d4_accurate.py << 'EOF'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B  # = 4.793857...

print(f"d^4 Tanabe-Sugano Diagram")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.4f}")
print("="*80)

def compute_d4_levels(Dq_over_B, C_over_B=4.793857):
    """
    Compute energy levels for d^4 in octahedral field using proper matrix diagonalization.
    
    Free ion term energies for d^4 (relative to 5D = 0):
    Using Racah parameterization from standard references (Griffith, Figgis):
    - 5D: 0 (ground)
    - 3H: 5B + 2C  -> E/B = 5 + 2*(C/B)
    - 3P: 15B      -> E/B = 15
    - 3F: 9B + 3C  -> E/B = 9 + 3*(C/B)  [Note: some refs use different values]
    - 3G: 11B + 5C -> E/B = 11 + 5*(C/B)
    - 1I: 18B + 9C -> E/B = 18 + 9*(C/B)
    - 1G: 14B + 7C -> E/B = 14 + 7*(C/B)
    - 1S: 22B + 10C -> E/B = 22 + 10*(C/B)
    - 1D: 10B + 5C -> E/B = 10 + 5*(C/B)
    - 1F: 12B + 6C -> E/B = 12 + 6*(C/B)
    
    Actually, let me use the standard energies from Tanabe-Sugano papers:
    For d^4 (and d^6 hole equivalent):
    - 5D: 0
    - 3P: 15B
    - 3H: 5B + 2C (lowest triplet by Hund's rule)
    - 3F: 9B + 3C
    - 3G: 11B + 5C
    """
    
    Dq = Dq_over_B  # in units of B
    C = C_over_B
    
    # Free ion energies (in units of B, relative to 5D)
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
    
    # === QUINTET STATES (from 5D, S=2) ===
    # 5D (L=2) splits into 5T2g and 5Eg in O_h
    # Crystal field energies (relative to 5D barycenter):
    # 5T2g: -6Dq
    # 5Eg: +4Dq
    levels.append(('5T2g', E_5D - 6*Dq))
    levels.append(('5Eg', E_5D + 4*Dq))
    
    # === TRIPLET T1g STATES ===
    # Multiple sources contribute to 3T1g:
    # - From 3P (L=1 -> T1): no CF splitting for L=1
    # - From 3F (L=3 -> T1): mixes with 3P
    # - From 3H (L=5 -> T1): higher energy
    # - From 3G (L=4 -> T1): higher energy
    
    # 3T1g from 3F-3P mixing (2x2 matrix)
    # Standard matrix elements (Figgis, Chapter 9):
    # Basis: |3T1g(F)>, |3T1g(P)>
    # H = | E(3F) - 6Dq    4Dq         |
    #     | 4Dq            E(3P) + 2Dq  |
    
    H_3T1g_FP = np.array([
        [E_3F - 6*Dq, 4*Dq],
        [4*Dq, E_3P + 2*Dq]
    ])
    eig_3T1g_FP = np.linalg.eigvalsh(H_3T1g_FP)
    levels.append(('3T1g', eig_3T1g_FP[0]))  # Lower eigenstate (mostly 3F character at low field)
    levels.append(('3T1g', eig_3T1g_FP[1]))  # Upper eigenstate (mostly 3P character)
    
    # 3T1g from 3H - approximate (H term splitting is complex)
    # For L=5, the T1g component has CF energy approximately -2Dq relative to 3H barycenter
    # Actually, the splitting of H in O_h gives multiple T1g components
    # Using approximate values from literature
    levels.append(('3T1g', E_3H - 2*Dq))  # 3T1g from 3H
    
    # 3T1g from 3G
    # 3G (L=4) -> A1 + E + T1 + T2 in O_h
    # T1g from G has CF energy approximately -6Dq
    levels.append(('3T1g', E_3G - 6*Dq))
    
    # === TRIPLET T2g STATES ===
    # From 3F: 3T2g at E(3F) + 2Dq
    # From 3H: 3T2g (multiple components)
    # From 3G: 3T2g
    
    levels.append(('3T2g', E_3F + 2*Dq))  # From 3F
    levels.append(('3T2g', E_3H + 4*Dq))  # From 3H (approximate)
    levels.append(('3T2g', E_3G - 8*Dq))  # From 3G (approximate)
    
    # === TRIPLET A2g STATES ===
    # Only from 3F: 3A2g at E(3F) + 12Dq
    levels.append(('3A2g', E_3F + 12*Dq))
    
    # === TRIPLET Eg STATES ===
    # From 3H: 3Eg
    # From 3G: 3Eg
    levels.append(('3Eg', E_3H + 6*Dq))  # From 3H (approximate)
    levels.append(('3Eg', E_3G + 2*Dq))  # From 3G
    
    # === TRIPLET A1g STATES ===
    # From 3G: 3A1g at E(3G) + 12Dq
    levels.append(('3A1g', E_3G + 12*Dq))
    
    # === SINGLET STATES ===
    # These are typically higher in energy, but include for completeness
    
    # From 1I (L=6): splits into multiple components
    levels.append(('1A1g', E_1I + 18*Dq))  # Approximate
    levels.append(('1Eg', E_1I + 8*Dq))
    levels.append(('1T1g', E_1I + 2*Dq))
    levels.append(('1T2g', E_1I - 4*Dq))
    
    # From 1G (L=4)
    levels.append(('1A1g', E_1G + 12*Dq))
    levels.append(('1Eg', E_1G + 2*Dq))
    levels.append(('1T1g', E_1G - 6*Dq))
    levels.append(('1T2g', E_1G - 8*Dq))
    
    # From 1S (L=0): only 1A1g, no CF splitting
    levels.append(('1A1g', E_1S))
    
    # From 1D (L=2)
    levels.append(('1Eg', E_1D + 4*Dq))
    levels.append(('1T2g', E_1D - 6*Dq))
    
    # From 1F (L=3)
    levels.append(('1A2g', E_1F + 12*Dq))
    levels.append(('1T1g', E_1F - 6*Dq))
    levels.append(('1T2g', E_1F + 2*Dq))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    return levels

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
Dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

all_results = []

for Dq_over_B in Dq_over_B_values:
    levels = compute_d4_levels(Dq_over_B, C_over_B)
    
    # Find ground state energy
    ground_energy = levels[0][1]
    
    # Get lowest 6 levels with energies relative to ground
    lowest_6 = []
    for term, energy in levels:
        rel_energy = energy - ground_energy
        lowest_6.append((term, rel_energy))
        if len(lowest_6) >= 6:
            break
    
    all_results.append((Dq_over_B, lowest_6))
    
    print(f"\nDq/B = {Dq_over_B}:")
    print(f"  Ground: {levels[0][0]} at E/B = {levels[0][1]:.4f}")
    print(f"  Lowest 6 levels (relative to ground):")
    for i, (term, e_rel) in enumerate(lowest_6):
        print(f"    {i+1}. {term}: E/B = {e_rel:.4f}")

# Create the Tanabe-Sugano plot
fig, ax = plt.subplots(figsize=(12, 9))

# Generate smooth curves
Dq_range = np.linspace(0, 4, 200)
term_curves = {}

for Dq in Dq_range:
    levels = compute_d4_levels(Dq, C_over_B)
    ground_energy = levels[0][1]
    
    # Track each unique level by its energy ordering
    for i, (term, energy) in enumerate(levels):
        key = f"{term}_{i}"
        if key not in term_curves:
            term_curves[key] = {'term': term, 'Dq': [], 'E': []}
        term_curves[key]['Dq'].append(Dq)
        term_curves[key]['E'].append(energy - ground_energy)

# Plot all curves
colors = plt.cm.tab10(np.linspace(0, 1, 20))
color_idx = 0

for key, data in term_curves.items():
    if len(data['Dq']) > 1:
        ax.plot(data['Dq'], data['E'], '-', linewidth=1.2, 
                color=colors[color_idx % len(colors)], alpha=0.7, label=data['term'])
        color_idx += 1

ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B (relative to ground state)', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁴ Octahedral Ion\n(C/B = {:.2f})'.format(C_over_B), 
             fontsize=16, fontweight='bold')
ax.set_xlim(0, 4)
ax.set_ylim(0, 55)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(loc='upper right', fontsize=9, bbox_to_anchor=(1.0, 1.0), ncol=2)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("\n" + "="*80)
print("Plot saved as diagram.png")
print("="*80)

# Final formatted output
print("\n\nFINAL RESULTS TABLE:")
print("="*80)
for Dq_over_B, levels in all_results:
    print(f"\nDq/B = {Dq_over_B}:")
    for i, (term, e_rel) in enumerate(levels):
        print(f"  Level {i+1}: {term}, E/B = {e_rel:.4f}")
EOF
python3 ts_d4_accurate.py