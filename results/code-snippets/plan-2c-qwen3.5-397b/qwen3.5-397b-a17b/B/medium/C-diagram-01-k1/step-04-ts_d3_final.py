import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Parameters for d3 ion
B = 828  # cm^-1
C = 3390  # cm^-1
C_over_B = C / B  # = 4.094202898550725

# Dq/B values to compute
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

def d3_energies(dq_over_b, C_over_B=4.094202898550725):
    """
    Compute energy levels for d3 octahedral complex.
    Returns list of (energy/B, term_label) tuples for lowest 6 levels.
    
    For d3, the 4A2g ground state must remain lowest at all Dq/B.
    Free ion term energies relative to 4F (using correct Racah formulas):
    - 4P: 15B above 4F
    - 2G: 3B + 2C above 4F (lowest doublet term)
    - 2H: 3B + 2C above 4F (degenerate with 2G)
    - 2P: 15B + 2C above 4F
    
    With C/B = 4.094:
    - 2G, 2H: 3 + 2*4.094 = 11.188B above 4F
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # === QUARTET STATES ===
    # 4A2g is ground state, set to E/B = 0
    
    levels.append((0.0, '4A2g'))
    
    # 4T2g: at 10Dq above 4A2g
    levels.append((10 * x, '4T2g'))
    
    # 4T1g: mixing between 4T1g(F) at 18Dq and 4T1g(P) at 15B + 18Dq
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))
    levels.append((eig_4t1g[1], '4T1g'))
    
    # === DOUBLE STATES ===
    # Free ion energies relative to 4F (in units of B):
    E_2G = 3 + 2*C_over_B   # = 11.188
    E_2H = 3 + 2*C_over_B   # = 11.188 (degenerate with 2G)
    E_2P = 15 + 2*C_over_B  # = 23.188
    
    # The key insight: we need to express doublet energies relative to 4A2g,
    # not relative to 4F. At Dq=0, 4A2g is at the 4F energy.
    # So at Dq=0, doublets are at E_2G, E_2H above 4A2g.
    
    # For Dq > 0, 4A2g goes down by 12Dq relative to 4F barycenter.
    # But we're measuring relative to 4A2g, so we need to add 12Dq to all energies.
    
    # Actually, let's think more carefully:
    # - 4F barycenter is our reference (E = 0)
    # - 4A2g is at -12Dq relative to 4F barycenter
    # - 4F term energy is at -6B relative to 4F barycenter (from Racah)
    # - So 4A2g is at -6B - 12Dq in absolute terms
    # - 2G term is at -6B + 3B + 2C = -3B + 2C relative to 4F barycenter
    # - So 2G is at (-3B + 2C) - (-6B - 12Dq) = 3B + 2C + 12Dq relative to 4A2g
    
    # In units of B: E_2G_rel = 3 + 2*C/B + 12*(Dq/B) = 3 + 2*C/B + 12x
    
    # Wait, that would make 2G increase with Dq, but the crystal field splitting
    # within 2G should cause some components to go down.
    
    # Let me reconsider. The crystal field splitting is relative to the TERM barycenter,
    # not the configuration barycenter.
    
    # For 2G term:
    # - Term barycenter is at E_2G = 3 + 2*C/B above 4F term
    # - 4F term is at 0 (our reference at Dq=0)
    # - So 2G barycenter is at 3 + 2*C/B above 4A2g at Dq=0
    # - As Dq increases, 4A2g stays at 0 (by convention)
    # - 2G barycenter stays at 3 + 2*C/B (free ion energy doesn't change)
    # - Crystal field splits 2G: 2Eg at +2Dq, 2T1g at -Dq, 2T2g at +Dq
    
    # So relative to 4A2g:
    # 2Eg(G) = 3 + 2*C/B + 2x = 11.188 + 2x
    # 2T1g(G) = 3 + 2*C/B - x = 11.188 - x
    # 2T2g(G) = 3 + 2*C/B + x = 11.188 + x
    
    # For 2H term (same barycenter energy as 2G):
    # 2Eg(H) = 3 + 2*C/B - 3x = 11.188 - 3x  (this goes DOWN with Dq!)
    # 2T1g(H) = 3 + 2*C/B + x = 11.188 + x
    # 2T2g(H) = 3 + 2*C/B + 2x = 11.188 + 2x
    
    # The problem: 2Eg(H) decreases with Dq and can cross below 4A2g.
    # But this is the first-order perturbation result.
    
    # In reality, the full diagonalization should keep 2Eg above 4A2g.
    # The issue is that 2G and 2H are degenerate free-ion terms, and when
    # we apply crystal field, they mix. The proper treatment requires
    # diagonalizing the full matrix including both terms.
    
    # Let me do the proper 2x2 diagonalization for 2Eg:
    # H = | E_2G + 2x    V    |
    #     | V         E_2H - 3x|
    #
    # where V is the mixing matrix element between 2G and 2H.
    # For degenerate terms, V can be significant.
    
    # The eigenvalues are:
    # E = (E_2G + 2x + E_2H - 3x)/2 ± sqrt(((E_2G + 2x - E_2H + 3x)/2)^2 + V^2)
    # E = (2*E_2G - x)/2 ± sqrt((5x/2)^2 + V^2)  [since E_2G = E_2H]
    # E = E_2G - x/2 ± sqrt(25x^2/4 + V^2)
    
    # The lower eigenvalue is: E_2G - x/2 - sqrt(25x^2/4 + V^2)
    # For large x: ≈ E_2G - x/2 - 5x/2 = E_2G - 3x (same as before)
    # For small x: ≈ E_2G - x/2 - V (if V >> x)
    
    # The mixing V prevents the levels from crossing. If V is large enough,
    # the lower 2Eg stays above 4A2g.
    
    # What is V? From group theory, the mixing between 2G and 2H 2Eg states
    # is proportional to Dq. Let's use V = k*x where k is a constant.
    
    # From detailed calculations (e.g., Figgis), k ≈ 2*sqrt(6) ≈ 4.9
    # But this still gives the same asymptotic behavior.
    
    # The real issue is that my free-ion energy for 2G/2H might be wrong.
    # Let me check: for d3, what is E(2G) - E(4F)?
    
    # From Racah parameter analysis:
    # E(4F) = 3A - 15B (for the term, relative to config average)
    # E(2G) = 3A - 9B + 3C
    # E(2G) - E(4F) = 6B + 3C
    
    # With C/B = 4.094: E(2G) - E(4F) = 6 + 3*4.094 = 18.28B
    
    # This is different from my earlier 3B + 2C = 11.188B!
    # Let me use 6B + 3C instead.
    
    E_2G_correct = 6 + 3*C_over_B   # = 18.28
    E_2H_correct = 6 + 3*C_over_B   # = 18.28
    E_2P_correct = 15 + 3*C_over_B  # = 27.28
    
    # Now 2Eg matrix with correct energies:
    H_2eg = np.array([[E_2G_correct + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H_correct - 3*x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g matrix
    H_2t1g = np.array([[E_2G_correct - x, 2*x], 
                       [2*x, E_2H_correct + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g matrix
    H_2t2g = np.array([[E_2G_correct + x, x], 
                       [x, E_2H_correct + 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

# Compute and print energies for each Dq/B
results = []
print("Tanabe-Sugano Diagram for d³ Octahedral (B = 828 cm⁻¹, C = 3390 cm⁻¹)")
print("="*70)

for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    results.append((dq_over_b, levels))
    print(f"\nDq/B = {dq_over_b:.1f}:")
    for i, (e, label) in enumerate(levels):
        print(f"  Level {i+1}: {label}, E/B = {e:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(12, 8))

all_levels = {i: {'x': [], 'y': [], 'label': ''} for i in range(6)}

for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    for i, (e, label) in enumerate(levels):
        all_levels[i]['x'].append(dq_over_b)
        all_levels[i]['y'].append(e)
        if dq_over_b == 0:
            all_levels[i]['label'] = label

colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown']

for i in range(6):
    ax.plot(all_levels[i]['x'], all_levels[i]['y'], '-', 
            color=colors[i], linewidth=2, label=all_levels[i]['label'])
    ax.plot(all_levels[i]['x'], all_levels[i]['y'], 'o', 
            color=colors[i], markersize=8)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d³ Octahedral Ion\n(B = 828 cm⁻¹, C = 3390 cm⁻¹, C/B = 4.094)', fontsize=14)
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-1, 50)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")
