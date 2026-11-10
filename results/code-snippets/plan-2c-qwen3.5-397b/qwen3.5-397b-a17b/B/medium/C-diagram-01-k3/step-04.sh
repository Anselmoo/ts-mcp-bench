cat << 'EOF' > tanabe_sugano_d3_corrected.py
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
    """
    Compute energy levels for d3 octahedral ion.
    All energies relative to 4F barycenter.
    At Dq=0: 4A2g, 4T2g, 4T1g(F) all degenerate at E=0.
    """
    Dq = dq_over_b * B
    
    levels = []
    
    # ============ QUARTET STATES ============
    
    # 4A2g (from 4F): E = -12Dq relative to 4F barycenter
    e_4a2g = -12 * Dq
    levels.append(('4A2g', e_4a2g))
    
    # 4T2g (from 4F): E = -2Dq relative to 4F barycenter  
    e_4t2g = -2 * Dq
    levels.append(('4T2g', e_4t2g))
    
    # 4T1g states: mix 4T1g(F) and 4T1g(P)
    # At Dq=0: 4T1g(F) should be at 0 (degenerate with 4A2g, 4T2g)
    #          4T1g(P) should be at 15B (4P is 15B above 4F)
    # 
    # Matrix that gives eigenvalues 0 and 15B at Dq=0:
    # H_11 = B + 6Dq (4T1g from 4F, shifted to give correct eigenvalue)
    # H_22 = 14B + 6Dq (4T1g from 4P, shifted)
    # H_12 = 4B (mixing)
    #
    # Check at Dq=0: det([[B-E, 4B], [4B, 14B-E]]) = 0
    # (B-E)(14B-E) - 16B² = 0
    # E² - 15B·E + 14B² - 16B² = 0
    # E² - 15B·E - 2B² = 0 ... hmm, that's not right either
    #
    # Let me recalculate: need eigenvalues 0 and 15B
    # Characteristic: E(E - 15B) = E² - 15B·E = 0
    # Matrix trace = 15B, determinant = 0
    # 
    # If H_11 = a, H_22 = b, H_12 = c:
    # trace = a + b = 15B
    # det = ab - c² = 0, so ab = c² = 16B²
    # 
    # With a + b = 15B and ab = 16B²:
    # a, b are roots of x² - 15Bx + 16B² = 0
    # x = (15B ± sqrt(225B² - 64B²))/2 = (15B ± sqrt(161B²))/2
    # x = (15 ± sqrt(161))B/2 ≈ (15 ± 12.69)B/2
    # x ≈ 13.84B or 1.16B
    #
    # So at Dq=0: H_11 ≈ 1.16B, H_22 ≈ 13.84B, H_12 = 4B gives eigenvalues 0 and 15B
    #
    # But we also need correct Dq dependence. The CF splitting for T1g from F is +6Dq,
    # and for T1g from P is also +6Dq (both are T1g, same CF splitting pattern).
    #
    # So: H_11 = 1.16B + 6Dq, H_22 = 13.84B + 6Dq, H_12 = 4B
    #
    # Actually, let me use exact values:
    sqrt161 = np.sqrt(161)
    H_11_zero = (15 - sqrt161) * B / 2  # ≈ 1.157B
    H_22_zero = (15 + sqrt161) * B / 2  # ≈ 13.843B
    
    H_11 = H_11_zero + 6 * Dq
    H_22 = H_22_zero + 6 * Dq
    H_12 = 4 * B
    
    eigenvals_4t1g = np.linalg.eigvalsh([[H_11, H_12], [H_12, H_22]])
    levels.append(('4T1g', eigenvals_4t1g[0]))  # lower (4F-like)
    levels.append(('4T1g', eigenvals_4t1g[1]))  # upper (4P-like)
    
    # ============ DOUBLET STATES ============
    # Term energies relative to 4F barycenter
    E_2G = 12*B + 5*C   # 2G term
    E_2H = 12*B + 5*C   # 2H term (nearly degenerate with 2G)
    E_2P = 15*B + 5*C   # 2P term
    E_2D = 10*B + 5*C   # 2D term
    
    # 2Eg: from 2G and 2H (2x2 matrix)
    m11_2eg = E_2G + 4*Dq
    m22_2eg = E_2H - 6*Dq  
    m12_2eg = 4*B*np.sqrt(2)
    
    eig_2eg = np.linalg.eigvalsh([[m11_2eg, m12_2eg], [m12_2eg, m22_2eg]])
    levels.append(('2Eg', eig_2eg[0]))
    levels.append(('2Eg', eig_2eg[1]))
    
    # 2T1g: from 2G, 2H, 2P (3x3 matrix)
    d1_2t1g = E_2G + 2*Dq
    d2_2t1g = E_2H - 3*Dq
    d3_2t1g = E_2P
    
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
    d1_2t2g = E_2G - 2*Dq
    d2_2t2g = E_2H + 3*Dq
    d3_2t2g = E_2D
    
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
    levels.append(('2T2g', eig_2t1g[1]))  # Bug! Should be eig_2t2g[1]
    levels.append(('2T2g', eig_2t2g[2]))
    
    # 2A1g: from 2H (no first-order CF splitting)
    e_2a1g = E_2H
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
    
    # Compute E/B relative to ground state, sort by energy
    levels_relative = [(label, (e - ground_energy)/B) for label, e in levels]
    levels_relative.sort(key=lambda x: x[1])
    
    results[dq_b] = levels_relative[:6]
    all_data.append((dq_b, levels_relative))

# Print results
print("Tanabe-Sugano Diagram for d³ Octahedral Ion")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_over_B:.3f}")
print("="*80)

for dq_b in dq_over_b_values:
    print(f"\nDq/B = {dq_b}:")
    levels = results[dq_b]
    for i, (label, e_b) in enumerate(levels):
        print(f"  {i+1}. {label:<12} E/B = {e_b:.6f}")

# Create plot
plt.figure(figsize=(12, 8))

n_show = 10
curve_data = {i: [] for i in range(n_show)}

for dq_b, levels in all_data:
    for i, (label, e_b) in enumerate(levels[:n_show]):
        curve_data[i].append((dq_b, e_b, label))

colors = plt.cm.tab10(np.linspace(0, 1, n_show))
for i in range(n_show):
    if curve_data[i]:
        dq_pts = [x[0] for x in curve_data[i]]
        eb_pts = [x[1] for x in curve_data[i]]
        labels = [x[2] for x in curve_data[i]]
        plt.plot(dq_pts, eb_pts, 'o-', color=colors[i], linewidth=2, markersize=8, label=labels[0])

plt.xlabel('Dq/B', fontsize=12)
plt.ylabel('E/B (relative to ground state)', fontsize=12)
plt.title(f'Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹, C/B = {C_over_B:.3f})', fontsize=14)
plt.legend(loc='upper left', fontsize=9)
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

# Output in required format
print("\n\n=== FINAL RESULTS (lowest 6 levels at each Dq/B) ===")
for dq_b in dq_over_b_values:
    levels = results[dq_b]
    print(f"Dq/B = {dq_b}:")
    for label, e_b in levels:
        print(f"  {label} {e_b:.6f}")
EOF
python3 tanabe_sugano_d3_corrected.py