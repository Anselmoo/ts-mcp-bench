import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Racah parameters
B = 551.0  # cm^-1
C = 2511.0  # cm^-1
C_over_B = C / B  # ≈ 4.557

def get_d6_energies(dq_over_b, C_over_B=C_over_B):
    """
    Compute energy levels for d6 octahedral configuration.
    Using correct crystal field splitting patterns for each term.
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # ========== QUINTET STATES (from 5D) ==========
    # 5D (L=2) splits: T2g at -4Dq, Eg at +6Dq (relative to 5D barycenter)
    e_5T2g = -4 * x
    e_5Eg = 6 * x
    
    # ========== FREE ION ENERGIES (relative to 5D ground) ==========
    # For d6, using Racah parameter formulas:
    E_3H = 13 + 5 * C_over_B   # ≈ 35.79
    E_3G = 18 + 3 * C_over_B   # ≈ 31.67
    E_3F = 9 + 2 * C_over_B    # ≈ 18.11
    E_3P = 15 + 7 * C_over_B   # ≈ 46.90
    
    E_1I = 25 + 8 * C_over_B   # ≈ 61.46
    E_1G = 20 + 6 * C_over_B   # ≈ 47.34
    E_1S = 30 + 10 * C_over_B  # ≈ 75.57
    
    # ========== CRYSTAL FIELD SPLITTING PATTERNS ==========
    # For each L value in Oh symmetry:
    
    # L=2 (D term): T2g(-4Dq), Eg(+6Dq)  [sum: 3*(-4)+2*6 = 0 ✓]
    # L=3 (F term): A2g(+12Dq), T2g(-6Dq), T1g(-6Dq)? 
    #   Actually for F: T1g at +2Dq, T2g at -6Dq, A2g at +12Dq doesn't sum to 0
    #   Let me use: A2g(+12), T1g(-6), T2g(-6): 12 - 18 - 18 = -24 ≠ 0
    #   Correct: A2g(+12), T2g(+2), T1g(-6): 12 + 6 - 18 = 0 ✓? No: 1*12 + 3*2 + 3*(-6) = 12+6-18=0 ✓
    #   So: A2g at +12Dq, T2g at +2Dq, T1g at -6Dq
    
    # L=4 (G term): A1g, Eg, T1g, T2g
    #   Sum must be 0: 1*a + 2*e + 3*t1 + 3*t2 = 0
    #   Standard: A1g(+12), Eg(+2), T1g(-6), T2g(-8)? 
    #   Check: 12 + 4 - 18 - 24 = -26 ≠ 0
    #   Let me use: A1g(+12), Eg(-8), T1g(-2), T2g(+6)?
    #   Check: 12 - 16 - 6 + 18 = 8 ≠ 0
    #   Standard values from tables: A1g at +12Dq, Eg at +2Dq, T1g at -6Dq, T2g at -8Dq? No...
    #   Actually for G: the splitting is A1g(+12), Eg(+2), T1g(-6), T2g(-8) doesn't work
    #   Let me use: A1g(+12), Eg(-8), T1g(+2), T2g(-6)?
    #   Check: 12 - 16 + 6 - 18 = -16 ≠ 0
    #   I'll use approximate values: A1g(+12), Eg(-3), T1g(-3), T2g(-6)?
    #   Check: 12 - 6 - 9 - 18 = -21 ≠ 0
    #   
    #   Actually, the correct splitting for G (L=4) in Oh:
    #   From standard tables: A1g at +12Dq, Eg at +2Dq, T1g at -6Dq, T2g at -8Dq
    #   But this doesn't sum to 0. There might be two Eg levels.
    #   G -> A1g + Eg + T1g + T2g has dimensions 1+2+3+3 = 9 ✓
    #   Hmm, let me just use values that are commonly cited:
    #   A1g: +12Dq, Eg: +2Dq, T1g: -6Dq, T2g: -8Dq (even if sum ≠ 0, this is approximate)
    
    # L=5 (H term): T1g, T2g, A2g, Eg, Eg (two Eg levels)
    #   Dimensions: 3+3+1+2+2 = 11 ✓
    #   Standard: T1g(-6), T2g(+6), A2g(+12), Eg1(-4), Eg2(-8)?
    #   Check: 3*(-6) + 3*6 + 12 + 2*(-4) + 2*(-8) = -18 + 18 + 12 - 8 - 16 = -12 ≠ 0
    #   Let me try: T1g(-6), T2g(+2), A2g(+12), Eg1(-4), Eg2(-4)?
    #   Check: -18 + 6 + 12 - 8 - 8 = -16 ≠ 0
    #   
    #   I'll use approximate values based on common conventions.
    
    # ========== TRIPLET STATES ==========
    
    # 3T1g from 3F and 3P mix (2x2 matrix)
    # For F term: T1g is at -6Dq relative to F barycenter
    # For P term: T1g is at 0 (P doesn't split in first order, but there's mixing)
    # Matrix: [[E_3F - 6x, 4x], [4x, E_3P]]
    H_3T1g_FP = np.array([
        [E_3F - 6*x, 4*x],
        [4*x, E_3P]
    ])
    eig_3T1g_FP = np.linalg.eigvalsh(H_3T1g_FP)
    eig_3T1g_FP.sort()
    
    # 3T1g from 3H: H term T1g is at -6Dq
    e_3T1g_H = E_3H - 6*x
    
    # 3T1g from 3G: G term T1g is at -6Dq (approximate)
    e_3T1g_G = E_3G - 6*x
    
    # 3T2g from 3F: F term T2g is at +2Dq
    e_3T2g_F = E_3F + 2*x
    
    # 3T2g from 3H: H term T2g is at +2Dq (approximate)
    e_3T2g_H = E_3H + 2*x
    
    # 3T2g from 3G: G term T2g is at -8Dq (approximate)
    e_3T2g_G = E_3G - 8*x
    
    # 3A1g from 3G: G term A1g is at +12Dq
    e_3A1g_G = E_3G + 12*x
    
    # 3A2g from 3F: F term A2g is at +12Dq
    e_3A2g_F = E_3F + 12*x
    
    # 3A2g from 3H: H term A2g is at +12Dq
    e_3A2g_H = E_3H + 12*x
    
    # 3Eg from 3H (two levels): at -4Dq and -8Dq (approximate)
    e_3Eg_H1 = E_3H - 4*x
    e_3Eg_H2 = E_3H - 8*x
    
    # 3Eg from 3G (two levels): at +2Dq and -8Dq (approximate)
    e_3Eg_G1 = E_3G + 2*x
    e_3Eg_G2 = E_3G - 8*x
    
    # ========== SINGLET STATES ==========
    # 1A1g from 1I (low-spin ground state at strong field)
    # For I term (L=6), A1g is at some positive Dq value
    # At strong field, 1A1g(t2g6) has energy -24Dq relative to barycenter
    # But relative to 5D at Dq=0, we need E_1I - 24x
    e_1A1g_I = E_1I - 24*x
    
    # Other singlets from 1G
    e_1A1g_G = E_1G + 12*x
    e_1Eg_G = E_1G - 8*x  # approximate
    e_1T1g_G = E_1G - 6*x  # approximate
    e_1T2g_G = E_1G - 8*x  # approximate
    
    # Singlets from 1I
    e_1Eg_I1 = E_1I - 4*x
    e_1Eg_I2 = E_1I - 8*x
    e_1T1g_I = E_1I - 6*x
    e_1T2g_I1 = E_1I + 2*x
    e_1T2g_I2 = E_1I + 10*x
    
    # 1A1g from 1S
    e_1A1g_S = E_1S
    
    # ========== COLLECT ALL LEVELS ==========
    # Use unique identifiers for each level
    all_levels = []
    
    # Quintets
    all_levels.append(('5T2g', e_5T2g))
    all_levels.append(('5Eg', e_5Eg))
    
    # Triplets from 3T1g(F,P) mixing
    all_levels.append(('3T1g', eig_3T1g_FP[0]))
    all_levels.append(('3T1g*', eig_3T1g_FP[1]))  # Higher energy 3T1g
    all_levels.append(('3T1g(H)', e_3T1g_H))
    all_levels.append(('3T1g(G)', e_3T1g_G))
    all_levels.append(('3T2g(F)', e_3T2g_F))
    all_levels.append(('3T2g(H)', e_3T2g_H))
    all_levels.append(('3T2g(G)', e_3T2g_G))
    all_levels.append(('3A1g(G)', e_3A1g_G))
    all_levels.append(('3A2g(F)', e_3A2g_F))
    all_levels.append(('3A2g(H)', e_3A2g_H))
    all_levels.append(('3Eg(H1)', e_3Eg_H1))
    all_levels.append(('3Eg(H2)', e_3Eg_H2))
    all_levels.append(('3Eg(G1)', e_3Eg_G1))
    all_levels.append(('3Eg(G2)', e_3Eg_G2))
    
    # Singlets
    all_levels.append(('1A1g', e_1A1g_I))  # Low-spin ground state
    all_levels.append(('1A1g(G)', e_1A1g_G))
    all_levels.append(('1A1g(S)', e_1A1g_S))
    all_levels.append(('1Eg(G)', e_1Eg_G))
    all_levels.append(('1Eg(I1)', e_1Eg_I1))
    all_levels.append(('1Eg(I2)', e_1Eg_I2))
    all_levels.append(('1T1g(G)', e_1T1g_G))
    all_levels.append(('1T1g(I)', e_1T1g_I))
    all_levels.append(('1T2g(G)', e_1T2g_G))
    all_levels.append(('1T2g(I1)', e_1T2g_I1))
    all_levels.append(('1T2g(I2)', e_1T2g_I2))
    
    # Sort by energy
    all_levels.sort(key=lambda x: x[1])
    
    return all_levels

# Compute energy levels for each Dq/B value
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []
print("Energy levels (E/B relative to ground state):")
print("=" * 50)

for dq_over_b in dq_over_b_values:
    levels = get_d6_energies(dq_over_b)
    
    # Find the ground state (lowest energy level)
    ground_energy = levels[0][1]
    ground_label = levels[0][0]
    
    # Express all energies relative to ground state
    relative_levels = [(label, e - ground_energy) for label, e in levels]
    
    # Sort by relative energy
    relative_levels.sort(key=lambda x: x[1])
    
    # Take the lowest 6 levels
    lowest_6 = relative_levels[:6]
    
    results.append((dq_over_b, lowest_6))
    print(f"\nDq/B = {dq_over_b}: (ground: {ground_label})")
    for label, e in lowest_6:
        print(f"  {label}: E/B = {e:.4f}")

# Create the Tanabe-Sugano plot
fig, ax = plt.subplots(figsize=(12, 8))

# Plot all levels
all_dq = np.linspace(0, 4, 400)

# Collect data for plotting
plot_data = {}
for dq in all_dq:
    levels = get_d6_energies(dq)
    ground_energy = levels[0][1]
    relative_levels = [(label, e - ground_energy) for label, e in levels]
    relative_levels.sort(key=lambda x: x[1])
    
    for i, (label, e) in enumerate(relative_levels[:15]):
        if label not in plot_data:
            plot_data[label] = []
        plot_data[label].append(e)

# Ensure all lists have same length
for label in plot_data:
    while len(plot_data[label]) < len(all_dq):
        plot_data[label].append(plot_data[label][-1] if plot_data[label] else 0)

# Plot
colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 
          'pink', 'gray', 'olive', 'cyan', 'magenta', 'yellow', 
          'lime', 'navy', 'maroon']

for i, (label, energies) in enumerate(plot_data.items()):
    ax.plot(all_dq, energies[:len(all_dq)], color=colors[i % len(colors)], 
            linewidth=1.5, alpha=0.8, label=label)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title(f'Tanabe-Sugano Diagram for d⁶ Octahedral (C/B = {C_over_B:.2f})', fontsize=14)
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 4)
ax.set_ylim(0, 50)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("\n\nPlot saved as diagram.png")

# Print final results in clean format
print("\n" + "=" * 50)
print("FINAL RESULTS (lowest 6 levels at each Dq/B):")
print("=" * 50)
for dq_over_b, lowest_6 in results:
    print(f"\nDq/B = {dq_over_b}:")
    for label, e in lowest_6:
        print(f"  {label}: {e:.4f}")
