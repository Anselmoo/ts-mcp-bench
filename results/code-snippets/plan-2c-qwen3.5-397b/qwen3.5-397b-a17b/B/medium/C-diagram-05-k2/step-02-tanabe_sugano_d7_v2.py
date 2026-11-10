import numpy as np
import matplotlib.pyplot as plt

# Tanabe-Sugano diagram for d^7 octahedral ion
# B = 859 cm^-1, C = 3660 cm^-1

B = 859.0
C = 3660.0

def calculate_d7_energies(Dq_over_B, B, C):
    """
    Calculate all energy levels for d^7 octahedral complex.
    Uses proper Tanabe-Sugano matrices for each symmetry.
    """
    Dq = Dq_over_B * B
    
    levels = []  # List of (energy, term_label)
    
    # ============== QUARTET STATES (S=3/2) ==============
    # From 4F and 4P free ion terms
    
    # 4A2g: from 4F only
    # Energy relative to 4F barycenter: +12Dq for d^7
    E_4A2g = 12 * Dq
    levels.append((E_4A2g, "4A2g"))
    
    # 4T2g: from 4F only
    # Energy relative to 4F barycenter: +2Dq for d^7
    E_4T2g = 2 * Dq
    levels.append((E_4T2g, "4T2g"))
    
    # 4T1g: two states from mixing of 4T1g(4F) and 4T1g(4P)
    # Matrix for d^7:
    # | -6Dq    4Dq   |
    # |  4Dq    15B   |
    H_4T1g = np.array([
        [-6*Dq, 4*Dq],
        [4*Dq, 15*B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append((eig_4T1g[0], "4T1g"))  # Lower (ground at weak field)
    levels.append((eig_4T1g[1], "4T1g(P)"))  # Higher (from 4P)
    
    # ============== DOUBLET STATES (S=1/2) ==============
    # Free ion energies relative to 4F ground state:
    # 2G: 5B + 2C
    # 2H: 5B + 2C  
    # 2P: 18B + 2C
    # 2F: 17B + 2C
    # 2D: two terms - complex mixing
    
    E_2G = 5*B + 2*C
    E_2H = 5*B + 2*C
    E_2P = 18*B + 2*C
    E_2F = 17*B + 2*C
    
    # For 2D terms, there are two that mix. Using approximate energies:
    # Lower 2D: ~5B + 2C (similar to 2G, 2H)
    # Upper 2D: ~20B + 2C
    E_2D_low = 5*B + 2*C
    E_2D_high = 20*B + 2*C
    
    # --- 2A1g: only from 2G ---
    # G -> A1 + E + T1 + T2 in Oh
    # For G term splitting, using proper crystal field matrices
    # The A1 component from G has energy shift
    E_2A1g = E_2G + 12*Dq  # Approximate (G term A1 goes up with Dq)
    levels.append((E_2A1g, "2A1g"))
    
    # --- 2A2g: only from 2F ---
    # F -> A2 + T1 + T2 in Oh
    # For F term: A2 at -12Dq relative to F barycenter (for d^7: +12Dq)
    E_2A2g = E_2F + 12*Dq
    levels.append((E_2A2g, "2A2g"))
    
    # --- 2Eg: from 2G, 2H, and two 2D terms ---
    # This is complex - multiple states of 2Eg symmetry mix
    # 2G -> 2Eg at some Dq-dependent energy
    # 2H -> 2Eg at some Dq-dependent energy
    # 2D (low) -> 2Eg
    # 2D (high) -> 2Eg
    
    # For G term: E component at approximately -2Dq relative to G barycenter
    # For d^7 convention, this becomes +2Dq? Let me use proper values.
    # Actually for G term in Oh, the E component energy depends on the matrix.
    # Using approximate: E from G at E_2G + 2*Dq
    E_2Eg_from_G = E_2G + 2*Dq
    
    # H term: E component - similar treatment
    E_2Eg_from_H = E_2H - 3*Dq  # Approximate
    
    # D terms: E is the only component (D -> E + T2)
    # For lower 2D: E at approximately -6Dq relative to D barycenter
    E_2Eg_from_D_low = E_2D_low - 6*Dq
    # For upper 2D:
    E_2Eg_from_D_high = E_2D_high + 4*Dq  # Approximate
    
    # These four 2Eg states may mix. For simplicity, treat them separately.
    levels.append((E_2Eg_from_G, "2Eg(G)"))
    levels.append((E_2Eg_from_H, "2Eg(H)"))
    levels.append((E_2Eg_from_D_low, "2Eg(D)"))
    levels.append((E_2Eg_from_D_high, "2Eg(D')"))
    
    # --- 2T1g: from 2G, 2H, 2P, 2F ---
    # G -> T1, H -> T1, P -> T1, F -> T1
    # Multiple 2T1g states that can mix
    
    E_2T1g_from_G = E_2G - 6*Dq  # Approximate
    E_2T1g_from_H = E_2H + 4*Dq  # Approximate
    E_2T1g_from_P = E_2P  # P term has no first-order splitting
    E_2T1g_from_F = E_2F - 6*Dq  # Approximate (F -> T1 at +6Dq, for d^7: -6Dq)
    
    levels.append((E_2T1g_from_G, "2T1g(G)"))
    levels.append((E_2T1g_from_H, "2T1g(H)"))
    levels.append((E_2T1g_from_P, "2T1g(P)"))
    levels.append((E_2T1g_from_F, "2T1g(F)"))
    
    # --- 2T2g: from 2G, 2H, two 2D terms, 2F ---
    # G -> T2, H -> T2, D (low) -> T2, D (high) -> T2, F -> T2
    
    E_2T2g_from_G = E_2G - 6*Dq  # Approximate
    E_2T2g_from_H = E_2H + 4*Dq  # Approximate
    E_2T2g_from_D_low = E_2D_low + 4*Dq  # D -> T2 at +4Dq relative to D
    E_2T2g_from_D_high = E_2D_high - 6*Dq
    E_2T2g_from_F = E_2F + 2*Dq  # F -> T2 at -2Dq, for d^7: +2Dq
    
    levels.append((E_2T2g_from_G, "2T2g(G)"))
    levels.append((E_2T2g_from_H, "2T2g(H)"))
    levels.append((E_2T2g_from_D_low, "2T2g(D)"))
    levels.append((E_2T2g_from_D_high, "2T2g(D')"))
    levels.append((E_2T2g_from_F, "2T2g(F)"))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    E_ground = levels[0][0]
    shifted_levels = [(E - E_ground, label) for E, label in levels]
    
    return shifted_levels

# Calculate for each Dq/B value
dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d^7 Octahedral (B = 859 cm^-1, C = 3660 cm^-1)")
print("="*80)

all_results = []
for dq_over_B in dq_over_B_values:
    levels = calculate_d7_energies(dq_over_B, B, C)
    
    # Get lowest 6 unique terms
    # The problem says count each term once regardless of orbital degeneracy
    # Terms of same symmetry from different free-ion terms are separate levels
    
    seen_labels = set()
    lowest_6 = []
    for E_over_B, label in levels:
        if label not in seen_labels:
            seen_labels.add(label)
            lowest_6.append((E_over_B, label))
            if len(lowest_6) == 6:
                break
    
    # If we don't have 6 unique labels, just take first 6
    if len(lowest_6) < 6:
        lowest_6 = levels[:6]
    
    all_results.append((dq_over_B, lowest_6))
    
    print(f"\nDq/B = {dq_over_B}:")
    for i, (E_over_B, label) in enumerate(lowest_6):
        print(f"  {i+1}. {label}: E/B = {E_over_B:.4f}")

# Now create the plot
print("\n" + "="*80)
print("Creating plot...")

# Collect all levels for plotting
plot_data = {}
for dq_over_B in dq_over_B_values:
    levels = calculate_d7_energies(dq_over_B, B, C)
    E_ground = levels[0][0]
    for E, label in levels:
        E_shifted = E - E_ground
        if label not in plot_data:
            plot_data[label] = []
        plot_data[label].append((dq_over_B, E_shifted/B))

# Sort labels to have consistent ordering
sorted_labels = sorted(plot_data.keys())

plt.figure(figsize=(12, 8))

colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

for i, label in enumerate(sorted_labels):
    points = plot_data[label]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    color = colors[i % len(colors)]
    plt.plot(xs, ys, color=color, label=label, linewidth=2)

plt.xlabel('Dq/B', fontsize=12)
plt.ylabel('E/B', fontsize=12)
plt.title('Tanabe-Sugano Diagram for d⁷ Octahedral Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)', fontsize=14)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
plt.grid(True, alpha=0.3)
plt.xlim(-0.1, 4.1)
plt.ylim(-1, 25)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("Plot saved as diagram.png")

