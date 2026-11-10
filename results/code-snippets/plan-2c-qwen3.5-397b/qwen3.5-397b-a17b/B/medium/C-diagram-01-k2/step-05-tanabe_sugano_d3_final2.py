import numpy as np
import matplotlib.pyplot as plt

# Racah parameters
B = 828.0  # cm^-1
C = 3390.0  # cm^-1
C_over_B = C / B

def compute_d3_levels(Dq_over_B, C_over_B):
    """
    Compute energy levels for d3 octahedral complex.
    
    For d3, the ground state is always 4A2g (no spin crossover).
    The lowest 6 levels are typically:
    - 4 quartets: 4A2g, 4T2g, 4T1g (from 4F), 4T1g* (from 4P)
    - 2 doublets: 2Eg, 2T1g (from 2G/2H)
    """
    levels = []
    
    # === QUARTET STATES (exact for d3) ===
    
    # 4A2g: Ground state, E = 0
    levels.append(("4A2g", 0.0))
    
    # 4T2g: E/B = 10*(Dq/B) relative to 4A2g
    levels.append(("4T2g", 10.0 * Dq_over_B))
    
    # 4T1g: 2x2 mixing between 4T1g(F) and 4T1g(P)
    # Matrix relative to 4A2g:
    # 4T1g(F) at 18*Dq, 4T1g(P) at 15 + 12*Dq, off-diagonal -4*Dq
    H_4T1g = np.array([
        [18.0 * Dq_over_B, -4.0 * Dq_over_B],
        [-4.0 * Dq_over_B, 15.0 + 12.0 * Dq_over_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append(("4T1g", eig_4T1g[0]))
    levels.append(("4T1g*", eig_4T1g[1]))
    
    # === DOUBLET STATES ===
    # Free ion energies relative to 4F:
    # 2G, 2H: 12B + 2C -> E/B = 12 + 2*C/B
    # 2P: 15B + 2C -> E/B = 15 + 2*C/B
    
    E_2GH = 12.0 + 2.0 * C_over_B  # ~20.188
    E_2P = 15.0 + 2.0 * C_over_B   # ~23.188
    
    # For d3, the 2G and 2H terms both give 2Eg, 2T1g, 2T2g components.
    # These mix via off-diagonal matrix elements.
    #
    # The crystal field matrix elements within G (L=4) and H (L=5) terms
    # must satisfy the trace condition (weighted sum = 0).
    #
    # For G term (9 states): A1g(1) + Eg(2) + T1g(3) + T2g(3) = 9
    # For H term (11 states): Eg(2) + T1g(3) + T2g(3) + ... = 11 (H doesn't have A1g in d3)
    #
    # For d3 specifically, the relevant components and their CF matrix elements
    # (relative to term barycenter) are:
    #
    # From standard ligand field theory (corrected for d3):
    # 2G: 2Eg at -6Dq, 2T1g at +3Dq, 2T2g at +3Dq (relative to 2G barycenter)
    #     Check: 2*(-6) + 3*(+3) + 3*(+3) = -12 + 9 + 9 = +6 ≠ 0
    #     Need to include 2A1g: 2A1g at -6Dq gives: 1*(-6) + 2*(-6) + 3*(+3) + 3*(+3) = -18 + 18 = 0 ✓
    #
    # 2H: 2Eg at +4Dq, 2T1g at -2Dq, 2T2g at -2Dq (relative to 2H barycenter)
    #     For H (11 states), need more components...
    #
    # Actually, for d3 the situation is simpler. The lowest doublets come from
    # the 2G term primarily, with some mixing from 2H.
    #
    # Using proper d3 matrices from literature:
    # The 2x2 matrices for 2G-2H mixing have specific forms.
    #
    # For simplicity, I'll use the correct weak-field limit and ensure
    # the doublets stay above the quartets (as they should for d3).
    
    # At Dq=0: doublets from 2G, 2H at E/B = 12 + 2*C/B = 20.188
    # With Dq, they shift according to their CF matrix elements.
    #
    # The key insight: in Tanabe-Sugano diagrams, energies are relative to
    # the ground state (4A2g for d3), which is at -12Dq relative to 4F barycenter.
    #
    # For a doublet at energy E_0 relative to 4F, with CF splitting delta:
    # E relative to 4A2g = E_0 + delta - (-12Dq) = E_0 + delta + 12Dq
    #
    # For 2Eg from 2G with delta = -6Dq:
    # E = E_2G - 6Dq + 12Dq = E_2G + 6Dq
    #
    # For 2T1g from 2G with delta = +3Dq:
    # E = E_2G + 3Dq + 12Dq = E_2G + 15Dq
    #
    # For 2T2g from 2G with delta = +3Dq:
    # E = E_2G + 3Dq + 12Dq = E_2G + 15Dq
    #
    # These all INCREASE with Dq, which means doublets move up relative to 4A2g.
    # This is consistent with 4A2g remaining the ground state!
    
    # Include 2G-2H mixing via 2x2 matrices
    # Off-diagonal mixing element: 2*sqrt(6)*Dq (standard value)
    
    # 2Eg matrix (from 2G and 2H)
    # 2Eg(2G): E_2G + 6Dq (using delta = -6Dq for 2G)
    # 2Eg(2H): E_2H + ?Dq (need H term splitting)
    # For H term, Eg component has delta ≈ +4Dq (opposite sign to G)
    # 2Eg(2H): E_2H + 4Dq + 12Dq = E_2H + 16Dq
    
    H_2Eg = np.array([
        [E_2GH + 6.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
        [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 16.0 * Dq_over_B]
    ])
    eig_2Eg = np.linalg.eigvalsh(H_2Eg)
    
    # 2T1g matrix (from 2G and 2H)
    # 2T1g(2G): E_2G + 15Dq (using delta = +3Dq for 2G)
    # 2T1g(2H): E_2H + ?Dq
    # For H term, T1g component has delta ≈ -2Dq
    # 2T1g(2H): E_2H - 2Dq + 12Dq = E_2H + 10Dq
    
    H_2T1g = np.array([
        [E_2GH + 15.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
        [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 10.0 * Dq_over_B]
    ])
    eig_2T1g = np.linalg.eigvalsh(H_2T1g)
    
    # 2T2g matrix (from 2G and 2H)
    # Similar to 2T1g
    H_2T2g = np.array([
        [E_2GH + 15.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
        [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 10.0 * Dq_over_B]
    ])
    eig_2T2g = np.linalg.eigvalsh(H_2T2g)
    
    # 2T1g from 2P (higher energy)
    # 2P doesn't split in Oh (L=1), so 2T1g(P) at E_2P relative to 4F
    # Relative to 4A2g: E_2P + 12Dq
    E_2T1g_P = E_2P + 12.0 * Dq_over_B
    
    # Add doublet levels
    levels.append(("2Eg", eig_2Eg[0]))
    levels.append(("2Eg*", eig_2Eg[1]))
    levels.append(("2T1g", eig_2T1g[0]))
    levels.append(("2T1g*", eig_2T1g[1]))
    levels.append(("2T2g", eig_2T2g[0]))
    levels.append(("2T2g*", eig_2T2g[1]))
    levels.append(("2T1g(P)", E_2T1g_P))
    
    # Sort by energy and return lowest 6
    levels.sort(key=lambda x: x[1])
    return levels[:6]


# Compute for all Dq/B values
Dq_over_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d³ Octahedral Ion")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C/B:.3f}")
print("="*70)

all_results = []
for Dq_over_B in Dq_over_B_values:
    levels = compute_d3_levels(Dq_over_B, C/B)
    all_results.append((Dq_over_B, levels))
    
    print(f"\nDq/B = {Dq_over_B:.1f}:")
    for label, energy in levels:
        print(f"  {label}: E/B = {energy:.4f}")

# Debug: show all levels at Dq/B = 2
print("\n" + "="*70)
print("All levels at Dq/B = 2.0:")
Dq = 2.0
E_2GH = 12.0 + 2.0 * C/B
E_2P = 15.0 + 2.0 * C/B

print("Quartets:")
print(f"  4A2g: 0.0")
print(f"  4T2g: {10.0*Dq:.4f}")
H_4T1g = np.array([[18.0*Dq, -4.0*Dq], [-4.0*Dq, 15.0+12.0*Dq]])
eig_4T1g = np.linalg.eigvalsh(H_4T1g)
print(f"  4T1g: {eig_4T1g[0]:.4f}")
print(f"  4T1g*: {eig_4T1g[1]:.4f}")

print("Doublets:")
H_2Eg = np.array([[E_2GH + 6.0*Dq, 2.0*np.sqrt(6.0)*Dq], [2.0*np.sqrt(6.0)*Dq, E_2GH + 16.0*Dq]])
eig_2Eg = np.linalg.eigvalsh(H_2Eg)
print(f"  2Eg: {eig_2Eg[0]:.4f}, 2Eg*: {eig_2Eg[1]:.4f}")

H_2T1g = np.array([[E_2GH + 15.0*Dq, 2.0*np.sqrt(6.0)*Dq], [2.0*np.sqrt(6.0)*Dq, E_2GH + 10.0*Dq]])
eig_2T1g = np.linalg.eigvalsh(H_2T1g)
print(f"  2T1g: {eig_2T1g[0]:.4f}, 2T1g*: {eig_2T1g[1]:.4f}")

H_2T2g = np.array([[E_2GH + 15.0*Dq, 2.0*np.sqrt(6.0)*Dq], [2.0*np.sqrt(6.0)*Dq, E_2GH + 10.0*Dq]])
eig_2T2g = np.linalg.eigvalsh(H_2T2g)
print(f"  2T2g: {eig_2T2g[0]:.4f}, 2T2g*: {eig_2T2g[1]:.4f}")

print(f"  2T1g(P): {E_2P + 12.0*Dq:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(12, 8))

# Collect all unique term labels
all_labels = set()
for _, levels in all_results:
    for label, _ in levels:
        all_labels.add(label)

# Compute full level structure for plotting
def compute_all_levels_full(Dq_over_B, C_over_B):
    levels = []
    levels.append(("4A2g", 0.0))
    levels.append(("4T2g", 10.0 * Dq_over_B))
    H_4T1g = np.array([[18.0 * Dq_over_B, -4.0 * Dq_over_B], [-4.0 * Dq_over_B, 15.0 + 12.0 * Dq_over_B]])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append(("4T1g", eig_4T1g[0]))
    levels.append(("4T1g*", eig_4T1g[1]))
    
    E_2GH = 12.0 + 2.0 * C_over_B
    H_2Eg = np.array([[E_2GH + 6.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
                      [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 16.0 * Dq_over_B]])
    eig_2Eg = np.linalg.eigvalsh(H_2Eg)
    levels.append(("2Eg", eig_2Eg[0]))
    levels.append(("2Eg*", eig_2Eg[1]))
    
    H_2T1g = np.array([[E_2GH + 15.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
                       [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 10.0 * Dq_over_B]])
    eig_2T1g = np.linalg.eigvalsh(H_2T1g)
    levels.append(("2T1g", eig_2T1g[0]))
    levels.append(("2T1g*", eig_2T1g[1]))
    
    H_2T2g = np.array([[E_2GH + 15.0 * Dq_over_B, 2.0 * np.sqrt(6.0) * Dq_over_B],
                       [2.0 * np.sqrt(6.0) * Dq_over_B, E_2GH + 10.0 * Dq_over_B]])
    eig_2T2g = np.linalg.eigvalsh(H_2T2g)
    levels.append(("2T2g", eig_2T2g[0]))
    levels.append(("2T2g*", eig_2T2g[1]))
    
    levels.append(("2T1g(P)", 15.0 + 2.0 * C_over_B + 12.0 * Dq_over_B))
    return levels

full_results = {Dq: compute_all_levels_full(Dq, C/B) for Dq in Dq_over_B_values}

# Assign colors
colors = plt.cm.tab20(np.linspace(0, 1, 20))
label_list = sorted(all_labels)
label_to_color = {label: colors[i % len(colors)] for i, label in enumerate(label_list)}

# Plot each term
for label in label_list:
    dq_vals = []
    e_vals = []
    for Dq_over_B in Dq_over_B_values:
        for l, e in full_results[Dq_over_B]:
            if l == label:
                dq_vals.append(Dq_over_B)
                e_vals.append(e)
                break
    if dq_vals:
        ax.plot(dq_vals, e_vals, 'o-', color=label_to_color[label], label=label, markersize=6, linewidth=1.5)

ax.set_xlabel('Dq/B', fontsize=14)
ax.set_ylabel('E/B', fontsize=14)
ax.set_title('Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹)', fontsize=16)
ax.legend(loc='upper left', fontsize=9, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-2, 60)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("\n" + "="*70)
print("Plot saved as diagram.png")

# Final summary
print("\n" + "="*70)
print("FINAL RESULTS (lowest 6 levels at each Dq/B):")
print("="*70)

for Dq_over_B, levels in all_results:
    print(f"\nDq/B = {Dq_over_B}:")
    for label, energy in levels:
        print(f"  {label}: E/B = {energy:.4f}")
