import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Parameters
B = 859.0  # cm^-1
C = 3660.0  # cm^-1
C_over_B = C / B  # ≈ 4.26

def tanabe_sugano_d7(Dq_over_B, B=1.0, C_over_B=4.26):
    """
    Compute energy levels for d7 octahedral ion.
    Returns list of (term_label, E/B) tuples for lowest 6 levels.
    
    Standard Tanabe-Sugano convention:
    - At Dq=0, all components of 4F are degenerate at E=0
    - 4P is at E=15B
    - Mixing between 4T1g(F) and 4T1g(P) develops as Dq increases
    """
    Dq = Dq_over_B * B
    C = C_over_B * B
    
    levels = []
    
    # ============ QUARTET STATES (S=3/2) ============
    
    # Free ion term energies (relative to 4F = 0):
    E_4F = 0
    E_4P = 15 * B
    
    # Crystal field splitting of 4F components (relative to 4F barycenter):
    # For d7: 4T1g at -6Dq, 4T2g at +2Dq, 4A2g at +12Dq
    E_4T1g_F = -6*Dq
    E_4T2g = 2*Dq
    E_4A2g = 12*Dq
    
    # Crystal field splitting of 4P (T term):
    # 4T1g from 4P shifts by -6Dq relative to 4P barycenter
    E_4T1g_P = E_4P - 6*Dq  # = 15B - 6Dq
    
    # 4T1g mixing matrix
    # Use mixing that vanishes at Dq=0 to match standard TS convention
    # The mixing matrix element scales with Dq (crystal field induced mixing)
    mixing = 4 * Dq  # Mixing proportional to Dq, vanishes at Dq=0
    
    H_4T1g = np.array([
        [E_4T1g_F, mixing],
        [mixing, E_4T1g_P]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    
    levels.append(('4T1g', eig_4T1g[0]))  # Lower 4T1g
    levels.append(('4T1g', eig_4T1g[1]))  # Upper 4T1g
    levels.append(('4T2g', E_4T2g))
    levels.append(('4A2g', E_4A2g))
    
    # ============ DOUBLET STATES (S=1/2) ============
    # Free ion doublet term energies (relative to 4F = 0):
    E_2D = 12*B + 5*C   # ≈ 33.3B (lowest doublet)
    E_2G = 15*B + 5*C   # ≈ 36.3B
    E_2H = 15*B + 5*C   # ≈ 36.3B
    E_2F = 15*B + 5*C   # ≈ 36.3B
    E_2P = 15*B + 10*C  # ≈ 57.6B
    E_2S = 20*B + 10*C  # ≈ 62.6B
    
    # Crystal field splitting of doublet terms:
    # 2D (L=2) -> 2Eg + 2T2g: T2g at -4Dq, Eg at +6Dq
    E_2T2g_D = E_2D - 4*Dq
    E_2Eg_D = E_2D + 6*Dq
    
    # 2G (L=4) -> 2Eg + 2T1g + 2T2g
    E_2Eg_G = E_2G - 5*Dq
    E_2T1g_G = E_2G - 2*Dq
    E_2T2g_G = E_2G + 3*Dq
    
    # 2H (L=5) -> 2Eg + 2T1g + 2T2g
    E_2Eg_H = E_2H + 5*Dq
    E_2T1g_H = E_2H + 2*Dq
    E_2T2g_H = E_2H - 3*Dq
    
    # 2F (L=3) -> 2A2g + 2T1g + 2T2g
    E_2A2g_F = E_2F + 6*Dq
    E_2T1g_F = E_2F - 3*Dq
    E_2T2g_F = E_2F + 2*Dq
    
    # 2P (L=1) -> 2T1g
    E_2T1g_P = E_2P - 6*Dq
    
    # 2S (L=0) -> 2A1g (no splitting)
    E_2A1g_S = E_2S
    
    # 2Eg: mix 2Eg from 2D and 2G
    mixing_2Eg = 2 * Dq  # Mixing proportional to Dq
    H_2Eg = np.array([
        [E_2Eg_D, mixing_2Eg],
        [mixing_2Eg, E_2Eg_G]
    ])
    eig_2Eg = np.linalg.eigvalsh(H_2Eg)
    levels.append(('2Eg', eig_2Eg[0]))
    levels.append(('2Eg', eig_2Eg[1]))
    
    # 2T1g: take lowest from available sources
    E_2T1g_lowest = min(E_2T1g_G, E_2T1g_H, E_2T1g_F, E_2T1g_P)
    levels.append(('2T1g', E_2T1g_lowest))
    
    # 2T2g: take lowest from available sources
    E_2T2g_lowest = min(E_2T2g_D, E_2T2g_G, E_2T2g_H, E_2T2g_F)
    levels.append(('2T2g', E_2T2g_lowest))
    
    # 2A1g from 2S
    levels.append(('2A1g', E_2A1g_S))
    
    # 2A2g from 2F
    levels.append(('2A2g', E_2A2g_F))
    
    # Sort by energy
    levels.sort(key=lambda x: x[1])
    
    # Shift so ground state is at 0
    E_ground = levels[0][1]
    levels = [(label, E - E_ground) for label, E in levels]
    
    # Convert to E/B
    levels = [(label, E/B) for label, E in levels]
    
    return levels[:6]  # Return lowest 6 levels

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
print("Tanabe-Sugano Diagram for d7 octahedral ion")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")
print("="*60)

results = []
for Dq_over_B in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
    levels = tanabe_sugano_d7(Dq_over_B, B=1.0, C_over_B=C_over_B)
    results.append((Dq_over_B, levels))
    print(f"\nDq/B = {Dq_over_B}:")
    for i, (label, E_over_B) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {E_over_B:.4f}")

# Create plot
fig, ax = plt.subplots(figsize=(10, 8))

for idx in range(6):
    energies = [levels[idx][1] for _, levels in results]
    ax.plot([r[0] for r in results], energies, 'o-', linewidth=2, markersize=8)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d⁷ Octahedral Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)', fontsize=14)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-1, 50)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()

print(f"\n\nPlot saved as diagram.png")
print(f"SHA256: {sha256_hash}")

