import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Tanabe-Sugano diagram for d^7 octahedral ion
# B = 859 cm^-1, C = 3660 cm^-1

B = 859.0
C = 3660.0

def calculate_d7_energies(Dq_over_B, B, C):
    """Calculate all energy levels for d^7 octahedral."""
    Dq = Dq_over_B * B
    
    # Free ion energies relative to 4F ground
    E_4F = 0
    E_4P = 15 * B
    E_2G = 5*B + 2*C
    E_2H = 5*B + 2*C
    E_2P = 18*B + 2*C
    E_2F = 17*B + 2*C
    E_2D1 = 5*B + 2*C  # Lower 2D
    E_2D2 = 20*B + 2*C  # Upper 2D
    
    levels = []
    
    # ============== QUARTET STATES ==============
    
    # 4F -> 4A2g + 4T2g + 4T1g (for d^7)
    # 4A2g at +12Dq, 4T2g at +2Dq, 4T1g at -6Dq relative to 4F
    levels.append((12*Dq, "4A2g"))
    levels.append((2*Dq, "4T2g"))
    
    # 4T1g: mixing of 4T1g(4F) and 4T1g(4P)
    H_4T1g = np.array([[-6*Dq, 4*Dq], [4*Dq, 15*B]])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append((eig_4T1g[0], "4T1g"))
    levels.append((eig_4T1g[1], "4T1g'"))
    
    # ============== DOUBLET STATES ==============
    
    # Crystal field splittings (for d^7)
    # G term: A1 at +12Dq, E at -6Dq, T1 at +2Dq, T2 at -2Dq
    levels.append((E_2G + 12*Dq, "2A1g"))  # 2A1g from 2G
    levels.append((E_2G - 6*Dq, "2Eg"))    # 2Eg from 2G
    levels.append((E_2G + 2*Dq, "2T1g"))   # 2T1g from 2G
    levels.append((E_2G - 2*Dq, "2T2g"))   # 2T2g from 2G
    
    # H term: E at -3Dq, T1 at +3Dq, T2 at 0 (approximate)
    levels.append((E_2H - 3*Dq, "2Eg'"))   # 2Eg from 2H
    levels.append((E_2H + 3*Dq, "2T1g'"))  # 2T1g from 2H
    levels.append((E_2H + 0*Dq, "2T2g'"))  # 2T2g from 2H
    
    # P term: T1 only, no splitting
    levels.append((E_2P, "2T1g''"))  # 2T1g from 2P
    
    # F term: A2 at +12Dq, T1 at -6Dq, T2 at +2Dq
    levels.append((E_2F + 12*Dq, "2A2g"))  # 2A2g from 2F
    levels.append((E_2F - 6*Dq, "2T1g'''"))  # 2T1g from 2F
    levels.append((E_2F + 2*Dq, "2T2g''"))  # 2T2g from 2F
    
    # D1 term: E at +6Dq, T2 at -4Dq
    levels.append((E_2D1 + 6*Dq, "2Eg''"))   # 2Eg from 2D1
    levels.append((E_2D1 - 4*Dq, "2T2g'''")) # 2T2g from 2D1
    
    # D2 term: E at +6Dq, T2 at -4Dq
    levels.append((E_2D2 + 6*Dq, "2Eg'''"))   # 2Eg from 2D2
    levels.append((E_2D2 - 4*Dq, "2T2g''''")) # 2T2g from 2D2
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    E_ground = levels[0][0]
    shifted_levels = [(E - E_ground, label) for E, label in levels]
    
    return shifted_levels

# Calculate for each Dq/B value
dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

all_results = []
for dq_over_B in dq_over_B_values:
    levels = calculate_d7_energies(dq_over_B, B, C)
    lowest_6 = levels[:6]
    all_results.append((dq_over_B, lowest_6))

# Print results in required format
print("Tanabe-Sugano Diagram for d^7 Octahedral (B = 859 cm^-1, C = 3660 cm^-1)")
print("="*80)
for dq_over_B, levels in all_results:
    print(f"Dq/B = {dq_over_B}:")
    for E_over_B, label in levels:
        print(f"  {label}: E/B = {E_over_B:.4f}")
    print()

# Create the plot
print("Creating plot...")

plot_data = {}
for dq_over_B in dq_over_B_values:
    levels = calculate_d7_energies(dq_over_B, B, C)
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

# Get sha256 of the file
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"SHA256: {sha256_hash}")

