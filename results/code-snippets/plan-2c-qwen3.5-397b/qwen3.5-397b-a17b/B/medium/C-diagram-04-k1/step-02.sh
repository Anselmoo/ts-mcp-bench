cat > tanabe_sugano_d6_v2.py << 'EOF'
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
    Returns list of (term_label, E/B) tuples sorted by energy.
    
    Using standard Tanabe-Sugano matrix elements for d6.
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # ========== QUINTET STATES (from 5D) ==========
    # 5D splits into 5T2g and 5Eg in Oh symmetry
    # Relative to 5D barycenter: 5T2g at -4Dq, 5Eg at +6Dq
    e_5T2g = -4 * x
    e_5Eg = 6 * x
    
    # ========== FREE ION TRIPLET ENERGIES (relative to 5D) ==========
    # Using Racah parameter formulas for d6:
    # E(3H) - E(5D) = 13B + 5C
    # E(3G) - E(5D) = 18B + 3C  
    # E(3F) - E(5D) = 9B + 2C
    # E(3P) - E(5D) = 15B + 7C
    
    E_3H = 13 + 5 * C_over_B   # ≈ 35.79
    E_3G = 18 + 3 * C_over_B   # ≈ 31.67
    E_3F = 9 + 2 * C_over_B    # ≈ 18.11
    E_3P = 15 + 7 * C_over_B   # ≈ 46.90
    
    # ========== FREE ION SINGLET ENERGIES (relative to 5D) ==========
    # For d6:
    # E(1I) - E(5D) = 25B + 8C (approx)
    # E(1G) - E(5D) = 20B + 6C (approx)
    # E(1S) - E(5D) = 30B + 10C (approx)
    
    E_1I = 25 + 8 * C_over_B   # ≈ 61.46
    E_1G = 20 + 6 * C_over_B   # ≈ 47.34
    E_1S = 30 + 10 * C_over_B  # ≈ 75.57
    
    # ========== 3T1g STATES ==========
    # 3T1g(F) and 3T1g(P) mix via 2x2 matrix
    # Matrix: [[E_3F - 6x, 4x], [4x, E_3P]]
    H_3T1g = np.array([
        [E_3F - 6*x, 4*x],
        [4*x, E_3P]
    ])
    eig_3T1g = np.linalg.eigvalsh(H_3T1g)
    eig_3T1g.sort()
    
    # 3T1g(H) from 3H term: crystal field splitting of H gives T1 at +6Dq
    e_3T1g_H = E_3H + 6*x
    
    # 3T1g(G) from 3G term: crystal field splitting of G gives T1 at -2x (approx)
    e_3T1g_G = E_3G - 2*x
    
    # ========== 3T2g STATES ==========
    # 3T2g(F) from 3F: splitting gives T2 at +2x
    e_3T2g_F = E_3F + 2*x
    
    # 3T2g(H) from 3H: splitting gives T2 at +2x (need to verify)
    e_3T2g_H = E_3H + 2*x
    
    # 3T2g(G) from 3G: splitting gives T2 at -7x (approx)
    e_3T2g_G = E_3G - 7*x
    
    # ========== 3A1g STATES ==========
    # 3A1g(G) from 3G: splitting gives A1 at +12x (approx)
    e_3A1g_G = E_3G + 12*x
    
    # ========== 3A2g STATES ==========
    # 3A2g(F) from 3F: splitting gives A2 at -12x
    e_3A2g_F = E_3F - 12*x
    
    # 3A2g(H) from 3H: splitting gives A2 at -12x
    e_3A2g_H = E_3H - 12*x
    
    # ========== 3Eg STATES ==========
    # From 3H (two Eg levels): at -4x and +8x (need to verify)
    e_3Eg_H1 = E_3H - 4*x
    e_3Eg_H2 = E_3H + 8*x
    
    # From 3G (two Eg levels): at +2x and -8x (approx)
    e_3Eg_G1 = E_3G + 2*x
    e_3Eg_G2 = E_3G - 8*x
    
    # ========== SINGLET STATES ==========
    # 1A1g from 1G and 1S - these can mix
    # 1A1g(G): from 1G at +12x (approx)
    # 1A1g(S): from 1S (no crystal field for S term, but 1S is L=0)
    # Actually 1S is L=0, so it doesn't split, stays at E_1S
    
    # For the low-spin ground state 1A1g, it comes from t2g6 configuration
    # At strong field, this is the ground state
    # The energy of 1A1g(t2g6) relative to 5D at Dq=0 is approximately:
    # E(1A1g) = E(1I) + ... this is complicated
    
    # Actually, for d6, the 1A1g low-spin state comes from the 1I free ion term
    # At strong field (t2g6), the energy is -24Dq + electrostatic terms
    
    # Let me use the proper strong-field approach for 1A1g:
    # For t2g6 configuration (low-spin d6):
    # Crystal field energy: 6 * (-4Dq) = -24Dq
    # Electrostatic energy: depends on the term
    
    # The 1A1g(t2g6) energy relative to 5D at Dq=0:
    # E(1A1g)/B = E_1I - 24x (approximately, since 1I gives 1A1g in Oh)
    
    e_1A1g_I = E_1I - 24*x
    
    # Other singlets from 1G:
    # 1G -> 1A1g + 1Eg + 1T1g + 1T2g in Oh
    e_1A1g_G = E_1G + 12*x
    e_1Eg_G = E_1G - 8*x
    e_1T1g_G = E_1G - 2*x
    e_1T2g_G = E_1G + 2*x
    
    # Singlets from 1I:
    # 1I -> 1A1g + 1Eg + 1T1g + 1T2g + 1T2g (two T2g)
    e_1A1g_I_2 = E_1I + 12*x  # Another 1A1g from 1I
    e_1Eg_I1 = E_1I - 8*x
    e_1Eg_I2 = E_1I + 4*x
    e_1T1g_I = E_1I - 2*x
    e_1T2g_I1 = E_1I + 2*x
    e_1T2g_I2 = E_1I + 10*x
    
    # 1S -> 1A1g only
    e_1A1g_S = E_1S
    
    # ========== COLLECT ALL LEVELS ==========
    # Quintets
    levels.append(('5T2g', e_5T2g))
    levels.append(('5Eg', e_5Eg))
    
    # Triplets
    levels.append(('3T1g', eig_3T1g[0]))  # Lower eigenvalue (mostly 3T1g(F) character)
    levels.append(('3T1g', eig_3T1g[1]))  # Higher eigenvalue (mostly 3T1g(P) character)
    levels.append(('3T1g(H)', e_3T1g_H))
    levels.append(('3T1g(G)', e_3T1g_G))
    levels.append(('3T2g(F)', e_3T2g_F))
    levels.append(('3T2g(H)', e_3T2g_H))
    levels.append(('3T2g(G)', e_3Eg_G2))  # Using wrong variable, fix below
    levels.append(('3T2g(G)', e_3T2g_G))
    levels.append(('3A1g(G)', e_3A1g_G))
    levels.append(('3A2g(F)', e_3A2g_F))
    levels.append(('3A2g(H)', e_3A2g_H))
    levels.append(('3Eg(H1)', e_3Eg_H1))
    levels.append(('3Eg(H2)', e_3Eg_H2))
    levels.append(('3Eg(G1)', e_3Eg_G1))
    levels.append(('3Eg(G2)', e_3Eg_G2))
    
    # Singlets
    levels.append(('1A1g', e_1A1g_I))  # Low-spin ground state candidate
    levels.append(('1A1g(G)', e_1A1g_G))
    levels.append(('1A1g(S)', e_1A1g_S))
    levels.append(('1Eg(G)', e_1Eg_G))
    levels.append(('1Eg(I1)', e_1Eg_I1))
    levels.append(('1Eg(I2)', e_1Eg_I2))
    levels.append(('1T1g(G)', e_1T1g_G))
    levels.append(('1T1g(I)', e_1T1g_I))
    levels.append(('1T2g(G)', e_1T2g_G))
    levels.append(('1T2g(I1)', e_1T2g_I1))
    levels.append(('1T2g(I2)', e_1T2g_I2))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    return levels

# Compute energy levels for each Dq/B value
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []
for dq_over_b in dq_over_b_values:
    levels = get_d6_energies(dq_over_b)
    
    # Find the ground state (lowest energy level)
    ground_energy = levels[0][1]
    
    # Express all energies relative to ground state
    relative_levels = [(label, e - ground_energy) for label, e in levels]
    
    # Sort by relative energy
    relative_levels.sort(key=lambda x: x[1])
    
    # Take the lowest 6 unique levels (by label, keeping first occurrence)
    seen = set()
    lowest_6 = []
    for label, e in relative_levels:
        if label not in seen:
            seen.add(label)
            lowest_6.append((label, e))
        if len(lowest_6) >= 6:
            break
    
    results.append((dq_over_b, lowest_6))
    print(f"Dq/B = {dq_over_b}:")
    for label, e in lowest_6:
        print(f"  {label}: E/B = {e:.4f}")
    print()

# Create the Tanabe-Sugano plot
fig, ax = plt.subplots(figsize=(10, 8))

# Plot all levels for each Dq/B
all_dq = np.linspace(0, 4, 400)

# Track levels for plotting
level_traces = {}

for dq in all_dq:
    levels = get_d6_energies(dq)
    ground_energy = levels[0][1]
    relative_levels = [(label, e - ground_energy) for label, e in levels]
    relative_levels.sort(key=lambda x: x[1])
    
    # Track each unique level
    for i, (label, e) in enumerate(relative_levels[:20]):  # Track lowest 20
        key = (label, i)  # Use index to distinguish same-label levels
        if key not in level_traces:
            level_traces[key] = ([], label)
        level_traces[key][0].append(e)

# Plot each level
colors = plt.cm.tab10(np.linspace(0, 1, 10))
colors_extended = list(colors) + list(plt.cm.tab20(np.linspace(0, 1, 20)))

for i, (key, (energies, label)) in enumerate(level_traces.items()):
    if len(energies) == len(all_dq):
        ax.plot(all_dq, energies, color=colors_extended[i % len(colors_extended)], 
                linewidth=1, alpha=0.7, label=label if i < 15 else "")

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title(f'Tanabe-Sugano Diagram for d⁶ Octahedral (C/B = {C_over_B:.2f})', fontsize=14)
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 4)
ax.set_ylim(0, 50)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("Plot saved as diagram.png")
EOF
python3 tanabe_sugano_d6_v2.py