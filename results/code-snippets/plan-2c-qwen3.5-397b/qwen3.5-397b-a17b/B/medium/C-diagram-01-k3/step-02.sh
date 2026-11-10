cat << 'EOF' > tanabe_sugano_d3_v2.py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Parameters for d3 ion
B = 828.0  # cm^-1
C = 3390.0  # cm^-1
C_over_B = C / B

# Dq/B values to compute
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

def compute_levels(dq_over_b, B, C):
    """Compute energy levels for d3 octahedral ion using correct TS matrices"""
    Dq = dq_over_b * B
    
    levels = []
    
    # ============ QUARTET STATES (from 4F and 4P) ============
    # Reference: energies relative to 4F barycenter
    
    # 4A2g (from 4F): E = -12Dq relative to 4F barycenter
    e_4a2g = -12 * Dq
    levels.append(('4A2g', e_4a2g))
    
    # 4T2g (from 4F): E = -2Dq relative to 4F barycenter
    e_4t2g = -2 * Dq
    levels.append(('4T2g', e_4t2g))
    
    # 4T1g states: mix 4T1g(F) and 4T1g(P)
    # 4T1g(F) is at +6Dq relative to 4F barycenter
    # 4T1g(P) is at 15B + 6Dq (4P is 15B above 4F)
    # Off-diagonal mixing = 4B
    H_11 = 6 * Dq           # 4T1g from 4F
    H_22 = 15 * B + 6 * Dq  # 4T1g from 4P
    H_12 = 4 * B
    
    eigenvals_4t1g = np.linalg.eigvalsh([[H_11, H_12], [H_12, H_22]])
    levels.append(('4T1g', eigenvals_4t1g[0]))  # lower (mainly 4F character)
    levels.append(('4T1g', eigenvals_4t1g[1]))  # upper (mainly 4P character)
    
    # ============ DOUBLET STATES ============
    # Term energies relative to 4F barycenter (from Racah parameters)
    # 2G: 12B + 5C
    # 2H: 12B + 5C (nearly degenerate with 2G)
    # 2P: 15B + 5C
    # 2D: 10B + 5C
    
    E_2G = 12*B + 5*C
    E_2H = 12*B + 5*C
    E_2P = 15*B + 5*C
    E_2D = 10*B + 5*C
    
    # 2Eg: from 2G and 2H (2x2 matrix)
    # Crystal field splitting coefficients from group theory
    # 2G -> 2Eg: +4Dq, 2H -> 2Eg: -6Dq (approximate)
    # Off-diagonal mixing from angular momentum coupling
    
    # Using standard TS diagram matrix elements:
    m11_2eg = E_2G + 4*Dq
    m22_2eg = E_2H - 6*Dq
    m12_2eg = 4*B*np.sqrt(2)
    
    eig_2eg = np.linalg.eigvalsh([[m11_2eg, m12_2eg], [m12_2eg, m22_2eg]])
    levels.append(('2Eg', eig_2eg[0]))
    levels.append(('2Eg', eig_2eg[1]))
    
    # 2T1g: from 2G, 2H, 2P (3x3 matrix)
    # CF splitting: 2G->2T1g: +2Dq, 2H->2T1g: -3Dq, 2P->2T1g: 0
    d1_2t1g = E_2G + 2*Dq
    d2_2t1g = E_2H - 3*Dq
    d3_2t1g = E_2P + 0*Dq
    
    # Off-diagonal mixing terms
    o12_2t1g = 2*B*np.sqrt(6)
    o13_2t1g = 2*B*np.sqrt(6)
    o23_2t1g = 4*B
    
    M_2t1g = np.array([
        [d1_2t1g, o12_2t1g, o13_2t1g],
        [o12_2t1g, d2_2t1g, o23_2t1g],
        [o13_2t1g, o23_2t1g, d3_2t1g]
    ])
    eig_2t1g = np.linalg.eigvalsh(M_2t1g)
    levels.append(('2T1g', eig_2t1g[0]))
    levels.append(('2T1g', eig_2t1g[1]))
    levels.append(('2T1g', eig_2t1g[2]))
    
    # 2T2g: from 2G, 2H, 2D (3x3 matrix)
    # CF splitting: 2G->2T2g: -2Dq, 2H->2T2g: +3Dq, 2D->2T2g: 0
    d1_2t2g = E_2G - 2*Dq
    d2_2t2g = E_2H + 3*Dq
    d3_2t2g = E_2D + 0*Dq
    
    o12_2t2g = 2*B*np.sqrt(6)
    o13_2t2g = 4*B
    o23_2t2g = 2*B*np.sqrt(6)
    
    M_2t2g = np.array([
        [d1_2t2g, o12_2t2g, o13_2t2g],
        [o12_2t2g, d2_2t2g, o23_2t2g],
        [o13_2t2g, o23_2t2g, d3_2t2g]
    ])
    eig_2t2g = np.linalg.eigvalsh(M_2t2g)
    levels.append(('2T2g', eig_2t2g[0]))
    levels.append(('2T2g', eig_2t2g[1]))
    levels.append(('2T2g', eig_2t2g[2]))
    
    # 2A1g: from 2H only (no first-order CF splitting for A symmetry from H)
    e_2a1g = E_2H + 0*Dq
    levels.append(('2A1g', e_2a1g))
    
    return levels

# Compute results
results = {}
all_data = []

for dq_b in dq_over_b_values:
    levels = compute_levels(dq_b, B, C)
    
    # Find ground state energy
    energies = [l[1] for l in levels]
    ground_energy = min(energies)
    
    # Compute E/B relative to ground state
    levels_relative = [(label, (e - ground_energy)/B) for label, e in levels]
    levels_relative.sort(key=lambda x: x[1])
    
    results[dq_b] = levels_relative[:6]
    all_data.append((dq_b, levels_relative))

# Print detailed results
print("Tanabe-Sugano Diagram for d3 Octahedral Ion")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")
print("="*80)

for dq_b in dq_over_b_values:
    print(f"\nDq/B = {dq_b}:")
    levels = results[dq_b]
    for i, (label, e_b) in enumerate(levels):
        print(f"  {i+1}. {label:<12} E/B = {e_b:.6f}")

# Create plot
plt.figure(figsize=(12, 8))

# Plot all levels
for dq_b, levels in all_data:
    for label, e_b in levels[:15]:  # Plot more levels for the diagram
        plt.plot(dq_b, e_b, 'bo', markersize=4)

# Connect points for each level type
# Group by approximate energy ordering
n_curves = 15
curve_data = {i: [] for i in range(n_curves)}

for dq_b, levels in all_data:
    for i, (label, e_b) in enumerate(levels[:n_curves]):
        curve_data[i].append((dq_b, e_b, label))

colors = plt.cm.tab20(np.linspace(0, 1, n_curves))
for i in range(n_curves):
    if curve_data[i]:
        dq_pts = [x[0] for x in curve_data[i]]
        eb_pts = [x[1] for x in curve_data[i]]
        labels = [x[2] for x in curve_data[i]]
        plt.plot(dq_pts, eb_pts, '-', color=colors[i], linewidth=1.5, label=labels[0] if dq_b == 0 else None)

plt.xlabel('Dq/B', fontsize=12)
plt.ylabel('E/B (relative to ground state)', fontsize=12)
plt.title(f'Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹, C/B = {C_over_B:.3f})', fontsize=14)
plt.grid(True, alpha=0.3)
plt.xlim(-0.1, 4.1)
plt.ylim(-2, 55)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")

# Output structured data
print("\n\n=== FINAL RESULTS ===")
for dq_b in dq_over_b_values:
    levels = results[dq_b]
    print(f"Dq/B = {dq_b}:")
    for label, e_b in levels:
        print(f"  {label} {e_b:.6f}")
EOF
python3 tanabe_sugano_d3_v2.py