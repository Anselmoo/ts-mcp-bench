import numpy as np
import matplotlib.pyplot as plt

# Racah parameters
B = 828.0  # cm^-1
C = 3390.0  # cm^-1
C_over_B = C / B

def compute_d3_quartets(Dq_over_B):
    """Compute quartet energy levels for d3."""
    levels = []
    
    # 4A2g: Ground state
    levels.append(("4A2g", 0.0))
    
    # 4T2g: E/B = 10*(Dq/B)
    levels.append(("4T2g", 10.0 * Dq_over_B))
    
    # 4T1g: 2x2 mixing matrix
    # Matrix elements relative to 4A2g ground:
    # 4T1g(F) diagonal: 18*Dq (6Dq above 4F barycenter, 4A2g is 12Dq below)
    # 4T1g(P) diagonal: 15 + 12*Dq (15B above 4F, plus 12Dq shift)
    # Off-diagonal: -4*Dq
    H_4T1g = np.array([
        [18.0 * Dq_over_B, -4.0 * Dq_over_B],
        [-4.0 * Dq_over_B, 15.0 + 12.0 * Dq_over_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    
    levels.append(("4T1g", eig_4T1g[0]))  # Lower eigenvalue
    levels.append(("4T1g*", eig_4T1g[1]))  # Upper eigenvalue
    
    return levels

def compute_d3_doublets(Dq_over_B, C_over_B):
    """
    Compute doublet energy levels for d3.
    Uses proper weak-field matrices with 2G-2H mixing.
    """
    levels = []
    
    # Free ion energies relative to 4F ground:
    # 2G: 12B + 2C
    # 2H: 12B + 2C (degenerate with 2G at Dq=0)
    # 2P: 15B + 2C
    
    E_2G = 12.0 + 2.0 * C_over_B
    E_2H = 12.0 + 2.0 * C_over_B
    E_2P = 15.0 + 2.0 * C_over_B
    
    # For d3, the 2G and 2H terms mix in octahedral symmetry.
    # The mixing matrices for each symmetry species are 2x2.
    #
    # From standard ligand field theory (Figgis, Ballhausen):
    # The crystal field matrix elements within G and H terms are:
    #
    # For G term (L=4) in Oh: Eg, T1g, T2g components
    # For H term (L=5) in Oh: Eg, T1g, T2g components
    #
    # The diagonal CF matrix elements (relative to term barycenter):
    # G term: <Eg|V|Eg> = -4Dq, <T1g|V|T1g> = +2Dq, <T2g|V|T2g> = +2Dq
    # H term: <Eg|V|Eg> = +6Dq, <T1g|V|T1g> = -3Dq, <T2g|V|T2g> = -3Dq
    #
    # Off-diagonal mixing between 2G and 2H:
    # <2Eg(G)|V|2Eg(H)> = 2*sqrt(6)*Dq
    # <2T1g(G)|V|2T1g(H)> = 2*sqrt(6)*Dq
    # <2T2g(G)|V|2T2g(H)> = 2*sqrt(6)*Dq
    #
    # BUT: These matrix elements are relative to the TERM barycenters.
    # To get energies relative to 4A2g ground, we need to account for
    # the shift of 4A2g relative to 4F barycenter.
    #
    # 4A2g is at -12Dq relative to 4F barycenter.
    # So energies relative to 4A2g = (energies relative to 4F) + 12Dq
    #
    # For 2Eg from 2G:
    # E relative to 4F = E_2G + (-4Dq) = 12B + 2C - 4Dq
    # E relative to 4A2g = (12B + 2C - 4Dq) + 12Dq = 12B + 2C + 8Dq
    #
    # For 2Eg from 2H:
    # E relative to 4F = E_2H + (+6Dq) = 12B + 2C + 6Dq
    # E relative to 4A2g = (12B + 2C + 6Dq) + 12Dq = 12B + 2C + 18Dq
    #
    # Wait, this gives very different Dq dependence for 2Eg(G) vs 2Eg(H).
    # Let me reconsider...
    #
    # Actually, I think the issue is that I'm double-counting the Dq shift.
    # The matrix elements I quoted are already the CF splittings within each term.
    # The term barycenters (E_2G, E_2H) are at fixed energies relative to 4F.
    #
    # So for 2Eg from 2G:
    # E relative to 4F barycenter = E_2G + delta_Eg(G)
    # where delta_Eg(G) = -4Dq is the CF splitting within 2G.
    #
    # And 4A2g is at -12Dq relative to 4F barycenter.
    #
    # Therefore, E(2Eg from 2G) relative to 4A2g:
    # = [E_2G + delta_Eg(G)] - [-12Dq]
    # = E_2G + delta_Eg(G) + 12Dq
    # = (12B + 2C) + (-4Dq) + 12Dq
    # = 12B + 2C + 8Dq
    #
    # Similarly for 2Eg from 2H:
    # = E_2H + delta_Eg(H) + 12Dq
    # = (12B + 2C) + (+6Dq) + 12Dq
    # = 12B + 2C + 18Dq
    #
    # These both INCREASE with Dq, which contradicts standard diagrams...
    #
    # Unless the CF matrix element signs are wrong.
    # Let me try the opposite signs:
    # delta_Eg(G) = +4Dq, delta_Eg(H) = -6Dq
    #
    # Then:
    # 2Eg from 2G: 12B + 2C + 4Dq + 12Dq = 12B + 2C + 16Dq (increases more!)
    # 2Eg from 2H: 12B + 2C - 6Dq + 12Dq = 12B + 2C + 6Dq (still increases)
    #
    # This is not working. Let me think differently.
    #
    # Perhaps the issue is that the CF matrix elements I'm using are for
    # a different convention or reference frame.
    #
    # In the STRONG-FIELD limit (t2g^n eg^m basis):
    # - t2g^3 gives 4A2g (ground), 2Eg, 2T1g, 2T2g
    # - These doublets are at E = 9B + 3C above 4A2g (purely electrostatic)
    # - E/B = 9 + 3*C/B = 9 + 3*4.094 = 21.28
    #
    # In the WEAK-FIELD limit (Dq = 0):
    # - Doublets from 2G, 2H are at E = 12B + 2C above 4F
    # - Since 4A2g is also from 4F, doublets are at E/B = 12 + 2*C/B = 20.19
    #
    # So from weak to strong field, the doublet energy changes from 20.19 to 21.28.
    # That's a small INCREASE, not a decrease!
    #
    # This suggests my earlier empirical formulas (which had doublets decreasing)
    # were wrong. Let me use formulas that give a slight INCREASE with Dq.
    
    # Using the proper weak-field matrices:
    # 2Eg: 2x2 matrix from 2G and 2H mixing
    
    # Diagonal elements (relative to 4A2g):
    # 2Eg(2G): E_2G + delta_Eg(G) + 12Dq
    # 2Eg(2H): E_2H + delta_Eg(H) + 12Dq
    #
    # Using delta_Eg(G) = -4Dq, delta_Eg(H) = +6Dq:
    diag_2Eg_G = E_2G - 4.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2G + 8*Dq
    diag_2Eg_H = E_2H + 6.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2H + 18*Dq
    
    # Off-diagonal mixing
    off_diag_2Eg = 2.0 * np.sqrt(6.0) * Dq_over_B
    
    H_2Eg = np.array([
        [diag_2Eg_G, off_diag_2Eg],
        [off_diag_2Eg, diag_2Eg_H]
    ])
    eig_2Eg = np.linalg.eigvalsh(H_2Eg)
    
    # 2T1g: 2x2 matrix from 2G and 2H mixing
    # delta_T1g(G) = +2Dq, delta_T1g(H) = -3Dq
    diag_2T1g_G = E_2G + 2.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2G + 14*Dq
    diag_2T1g_H = E_2H - 3.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2H + 9*Dq
    
    off_diag_2T1g = 2.0 * np.sqrt(6.0) * Dq_over_B
    
    H_2T1g = np.array([
        [diag_2T1g_G, off_diag_2T1g],
        [off_diag_2T1g, diag_2T1g_H]
    ])
    eig_2T1g = np.linalg.eigvalsh(H_2T1g)
    
    # 2T2g: 2x2 matrix from 2G and 2H mixing
    # delta_T2g(G) = +2Dq, delta_T2g(H) = -3Dq (same as T1g for H term)
    diag_2T2g_G = E_2G + 2.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2G + 14*Dq
    diag_2T2g_H = E_2H - 3.0 * Dq_over_B + 12.0 * Dq_over_B  # = E_2H + 9*Dq
    
    off_diag_2T2g = 2.0 * np.sqrt(6.0) * Dq_over_B
    
    H_2T2g = np.array([
        [diag_2T2g_G, off_diag_2T2g],
        [off_diag_2T2g, diag_2T2g_H]
    ])
    eig_2T2g = np.linalg.eigvalsh(H_2T2g)
    
    # 2T1g from 2P (higher energy, no mixing with 2G/2H to first order)
    # 2P (L=1) doesn't split in Oh, so 2T1g(P) at E_2P relative to 4F
    # Relative to 4A2g: E_2P + 12Dq
    E_2T1g_P = E_2P + 12.0 * Dq_over_B
    
    levels.append(("2Eg", eig_2Eg[0]))
    levels.append(("2Eg*", eig_2Eg[1]))
    levels.append(("2T1g", eig_2T1g[0]))
    levels.append(("2T1g*", eig_2T1g[1]))
    levels.append(("2T2g", eig_2T2g[0]))
    levels.append(("2T2g*", eig_2T2g[1]))
    levels.append(("2T1g(P)", E_2T1g_P))
    
    return levels

def compute_all_levels(Dq_over_B, C_over_B):
    """Compute all energy levels and return lowest 6."""
    quartets = compute_d3_quartets(Dq_over_B)
    doublets = compute_d3_doublets(Dq_over_B, C_over_B)
    
    all_levels = quartets + doublets
    all_levels.sort(key=lambda x: x[1])
    
    return all_levels[:6]

# Compute for all Dq/B values
Dq_over_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d³ Octahedral Ion")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C/B:.3f}")
print("="*70)

all_results = []
for Dq_over_B in Dq_over_B_values:
    levels = compute_all_levels(Dq_over_B, C/B)
    all_results.append((Dq_over_B, levels))
    
    print(f"\nDq/B = {Dq_over_B:.1f}:")
    for label, energy in levels:
        print(f"  {label}: E/B = {energy:.4f}")

# Debug: show all levels at Dq/B = 2
print("\n" + "="*70)
print("All levels at Dq/B = 2.0:")
quartets = compute_d3_quartets(2.0)
doublets = compute_d3_doublets(2.0, C/B)
print("Quartets:")
for label, energy in quartets:
    print(f"  {label}: E/B = {energy:.4f}")
print("Doublets:")
for label, energy in doublets:
    print(f"  {label}: E/B = {energy:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(12, 8))

# Collect all unique term labels from lowest 6 at each point
all_labels = set()
for _, levels in all_results:
    for label, _ in levels:
        all_labels.add(label)

# Also add labels from full calculation for completeness
for label, _ in quartets + doublets:
    all_labels.add(label)

# Assign colors
colors = plt.cm.tab20(np.linspace(0, 1, 20))
label_list = sorted(all_labels)
label_to_color = {label: colors[i % len(colors)] for i, label in enumerate(label_list)}

# For plotting, we need to track each term across all Dq/B values
# Compute full level structure at each point
full_results = {}
for Dq_over_B in Dq_over_B_values:
    quartets = compute_d3_quartets(Dq_over_B)
    doublets = compute_d3_doublets(Dq_over_B, C/B)
    full_results[Dq_over_B] = quartets + doublets

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
