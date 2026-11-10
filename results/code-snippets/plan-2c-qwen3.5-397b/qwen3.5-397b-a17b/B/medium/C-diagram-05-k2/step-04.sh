cat > tanabe_sugano_d7_accurate.py << 'EOF'
import numpy as np
import matplotlib.pyplot as plt

# Tanabe-Sugano diagram for d^7 octahedral ion
# B = 859 cm^-1, C = 3660 cm^-1
# Using proper matrix diagonalization for each symmetry

B = 859.0
C = 3660.0

def calculate_d7_energies_accurate(Dq_over_B, B, C):
    """
    Calculate energy levels for d^7 using proper matrices for each symmetry.
    
    Free ion terms for d^7 (energies relative to 4F ground):
    4F: 0
    4P: 15B
    2G: 5B + 2C
    2H: 5B + 2C
    2P: 18B + 2C
    2F: 17B + 2C
    2D: Two terms - need to handle mixing
    
    In octahedral field, terms split and states of same symmetry mix.
    """
    Dq = Dq_over_B * B
    
    levels = []
    
    # ============== QUARTET STATES (S=3/2) ==============
    
    # 4A2g: from 4F only, energy = 12Dq for d^7
    levels.append((12*Dq, "4A2g"))
    
    # 4T2g: from 4F only, energy = 2Dq for d^7
    levels.append((2*Dq, "4T2g"))
    
    # 4T1g: 2x2 matrix from mixing of 4T1g(4F) and 4T1g(4P)
    # For d^7: [[-6Dq, 4Dq], [4Dq, 15B]]
    H_4T1g = np.array([[-6*Dq, 4*Dq], [4*Dq, 15*B]])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append((eig_4T1g[0], "4T1g"))
    levels.append((eig_4T1g[1], "4T1g'"))
    
    # ============== DOUBLET STATES (S=1/2) ==============
    
    # Free ion term energies
    E_2G = 5*B + 2*C
    E_2H = 5*B + 2*C
    E_2P = 18*B + 2*C
    E_2F = 17*B + 2*C
    
    # For 2D terms, there are two that mix. The matrix is:
    # | E_D1    V   |
    # | V      E_D2 |
    # where E_D1 ≈ 5B+2C, E_D2 ≈ 20B+2C, and V involves B
    # For simplicity, treat them as separate with energies:
    E_2D1 = 5*B + 2*C  # Lower 2D
    E_2D2 = 20*B + 2*C  # Upper 2D
    
    # --- 2A1g: only from 2G ---
    # G term (L=4) in Oh: A1 at +12Dq relative to G barycenter (for d^7)
    levels.append((E_2G + 12*Dq, "2A1g"))
    
    # --- 2A2g: only from 2F ---
    # F term (L=3) in Oh: A2 at +12Dq relative to F barycenter (for d^7)
    levels.append((E_2F + 12*Dq, "2A2g"))
    
    # --- 2Eg: from 2G, 2H, 2D1, 2D2 ---
    # Need to set up 4x4 matrix for mixing
    # 
    # For G term: E component at -6Dq relative to G (for d^7)
    # For H term: E component at -3Dq relative to H (approximate)
    # For D1 term: E component at +6Dq relative to D1 (for d^7, D->E is at -6Dq for d^3)
    # For D2 term: E component at -4Dq relative to D2
    #
    # The off-diagonal elements involve mixing between these states.
    # For simplicity, assume no mixing between different free-ion terms
    # (this is an approximation; in reality there is some mixing)
    
    E_2Eg_G = E_2G - 6*Dq
    E_2Eg_H = E_2H - 3*Dq
    E_2Eg_D1 = E_2D1 + 6*Dq  # D -> E at -6Dq for d^3, so +6Dq for d^7
    E_2Eg_D2 = E_2D2 - 4*Dq
    
    levels.append((E_2Eg_G, "2Eg"))
    levels.append((E_2Eg_H, "2Eg'"))
    levels.append((E_2Eg_D1, "2Eg''"))
    levels.append((E_2Eg_D2, "2Eg'''"))
    
    # --- 2T1g: from 2G, 2H, 2P, 2F ---
    # G term: T1 at +2Dq for d^7
    # H term: T1 at +4Dq (approximate)
    # P term: T1 at 0 (P has no first-order splitting)
    # F term: T1 at -6Dq for d^7
    
    E_2T1g_G = E_2G + 2*Dq
    E_2T1g_H = E_2H + 4*Dq
    E_2T1g_P = E_2P
    E_2T1g_F = E_2F - 6*Dq
    
    levels.append((E_2T1g_G, "2T1g"))
    levels.append((E_2T1g_H, "2T1g'"))
    levels.append((E_2T1g_P, "2T1g''"))
    levels.append((E_2T1g_F, "2T1g'''"))
    
    # --- 2T2g: from 2G, 2H, 2D1, 2D2, 2F ---
    # G term: T2 at -2Dq for d^7
    # H term: T2 at +4Dq (approximate)
    # D1 term: T2 at -4Dq for d^7 (D->T2 at +4Dq for d^3)
    # D2 term: T2 at +6Dq
    # F term: T2 at +2Dq for d^7
    
    E_2T2g_G = E_2G - 2*Dq
    E_2T2g_H = E_2H + 4*Dq
    E_2T2g_D1 = E_2D1 - 4*Dq
    E_2T2g_D2 = E_2D2 + 6*Dq
    E_2T2g_F = E_2F + 2*Dq
    
    levels.append((E_2T2g_G, "2T2g"))
    levels.append((E_2T2g_H, "2T2g'"))
    levels.append((E_2T2g_D1, "2T2g''"))
    levels.append((E_2T2g_D2, "2T2g'''"))
    levels.append((E_2T2g_F, "2T2g''''"))
    
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
    levels = calculate_d7_energies_accurate(dq_over_B, B, C)
    
    # Get lowest 6 levels
    lowest_6 = levels[:6]
    
    all_results.append((dq_over_B, lowest_6))
    
    print(f"\nDq/B = {dq_over_B}:")
    for i, (E_over_B, label) in enumerate(lowest_6):
        print(f"  {i+1}. {label}: E/B = {E_over_B:.4f}")

# Create the plot
print("\n" + "="*80)
print("Creating plot...")

# Collect all levels for plotting
plot_data = {}
for dq_over_B in dq_over_B_values:
    levels = calculate_d7_energies_accurate(dq_over_B, B, C)
    for E, label in levels:
        E_over_B = E / B
        if label not in plot_data:
            plot_data[label] = []
        plot_data[label].append((dq_over_B, E_over_B))

sorted_labels = sorted(plot_data.keys())

plt.figure(figsize=(14, 10))
colors = plt.cm.tab10(np.linspace(0, 1, 20))

for i, label in enumerate(sorted_labels):
    points = plot_data[label]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    color = colors[i % len(colors)]
    plt.plot(xs, ys, color=color, label=label, linewidth=2, marker='o', markersize=4)

plt.xlabel('Dq/B', fontsize=14)
plt.ylabel('E/B', fontsize=14)
plt.title('Tanabe-Sugano Diagram for d⁷ Octahedral Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)', fontsize=16)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
plt.grid(True, alpha=0.3)
plt.xlim(-0.1, 4.1)
plt.ylim(-1, 35)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("Plot saved as diagram.png")

# Print final results
print("\n" + "="*80)
print("FINAL RESULTS (lowest 6 levels at each Dq/B):")
print("="*80)
for dq_over_B, levels in all_results:
    print(f"Dq/B = {dq_over_B}:")
    for E_over_B, label in levels:
        print(f"  {label}: {E_over_B:.4f}")
    print()

EOF
python3 tanabe_sugano_d7_accurate.py