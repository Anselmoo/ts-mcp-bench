import numpy as np
import matplotlib.pyplot as plt

# Parameters
B = 859.0  # cm^-1
C = 3660.0  # cm^-1
C_over_B = C / B  # ≈ 4.26

def tanabe_sugano_d7(Dq_over_B, B=1.0, C_over_B=4.26):
    """
    Compute energy levels for d7 octahedral ion.
    Returns list of (term_label, E/B) tuples for lowest 6 levels.
    
    For d7, we use the hole formalism: d7 = 3 holes, similar to d3 but with reversed Dq.
    Free ion terms: 4F (ground), 4P, 2G, 2H, 2P, 2D, 2F, 2S
    
    In Oh symmetry:
    4F -> 4A2g + 4T2g + 4T1g
    4P -> 4T1g (mixes with 4T1g from 4F)
    2G -> 2Eg + 2T1g + 2T2g
    2H -> 2Eg + 2T1g + 2T2g  
    2P -> 2T1g
    2D -> 2Eg + 2T2g
    2F -> 2A2g + 2T1g + 2T2g
    2S -> 2A1g
    """
    Dq = Dq_over_B * B
    C = C_over_B * B
    
    levels = []
    
    # ============ QUARTET STATES (S=3/2) ============
    
    # 4T1g states: mixing of 4T1g(F) and 4T1g(P)
    # For d7 (using hole formalism with reversed Dq sign convention):
    # The 2x2 matrix for 4T1g:
    # Diagonal elements relative to 4F barycenter:
    # E(4T1g from 4F) = -6*Dq
    # E(4T1g from 4P) = 15*B - 6*Dq  (4P is at 15B above 4F)
    # Off-diagonal mixing: 4*B
    
    H_4T1g = np.array([
        [-6*Dq, 4*B],
        [4*B, 15*B - 6*Dq]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    levels.append(('4T1g', eig_4T1g[0]))  # Lower (mainly 4F character at low Dq)
    levels.append(('4T1g', eig_4T1g[1]))  # Upper (mainly 4P character)
    
    # 4T2g from 4F: E = +2*Dq (relative to 4F barycenter)
    levels.append(('4T2g', 2*Dq))
    
    # 4A2g from 4F: E = +12*Dq (relative to 4F barycenter)
    levels.append(('4A2g', 12*Dq))
    
    # ============ DOUBLET STATES (S=1/2) ============
    # These come from 2G, 2H, 2P, 2D, 2F, 2S free ion terms
    
    # Free ion term energies relative to 4F (using Racah parameters):
    # E(2G) = 15B + 5C ≈ 15B + 5*4.26B = 36.3B
    # E(2H) = 15B + 5C ≈ 36.3B (degenerate with 2G in free ion)
    # E(2P) = 15B + 10C ≈ 15B + 42.6B = 57.6B
    # E(2D) = 10B + 5C ≈ 10B + 21.3B = 31.3B
    # E(2F) = 15B + 5C ≈ 36.3B
    # E(2S) = 20B + 10C ≈ 20B + 42.6B = 62.6B
    
    # More accurate energies from Racah's formulas for d7:
    # Using the formulas from standard references:
    E_2G = 15*B + 5*C  # ≈ 36.3B
    E_2H = 15*B + 5*C  # ≈ 36.3B  
    E_2P = 15*B + 10*C  # ≈ 57.6B
    E_2D = 10*B + 5*C  # ≈ 31.3B
    E_2F = 15*B + 5*C  # ≈ 36.3B
    E_2S = 20*B + 10*C  # ≈ 62.6B
    
    # 2Eg states: from 2G, 2H, 2D
    # Need to set up 3x3 matrix for 2Eg
    # Crystal field splitting for 2Eg from each term:
    # 2G -> 2Eg: -5Dq (approx)
    # 2H -> 2Eg: +5Dq (approx)
    # 2D -> 2Eg: +5Dq (approx)
    
    # Simplified: just use diagonal energies with Dq dependence
    # 2Eg from 2G
    E_2Eg_G = E_2G - 5*Dq
    # 2Eg from 2H  
    E_2Eg_H = E_2H + 5*Dq
    # 2Eg from 2D
    E_2Eg_D = E_2D + 5*Dq
    
    # 2x2 mixing for lowest two 2Eg (from 2G and 2D, which are closest)
    H_2Eg = np.array([
        [E_2Eg_G, 2*B],
        [2*B, E_2Eg_D]
    ])
    eig_2Eg = np.linalg.eigvalsh(H_2Eg)
    levels.append(('2Eg', eig_2Eg[0]))
    levels.append(('2Eg', eig_2Eg[1]))
    
    # 2T1g states: from 2G, 2H, 2P, 2F
    # Crystal field splitting (approximate):
    E_2T1g_G = E_2G - 2*Dq
    E_2T1g_H = E_2H + 2*Dq
    E_2T1g_P = E_2P - 2*Dq
    E_2T1g_F = E_2F + 3*Dq
    
    # Take lowest (from 2G)
    levels.append(('2T1g', E_2T1g_G))
    
    # 2T2g states: from 2G, 2H, 2D, 2F
    E_2T2g_G = E_2G + 3*Dq
    E_2T2g_H = E_2H - 3*Dq
    E_2T2g_D = E_2D - 5*Dq
    E_2T2g_F = E_2F - 2*Dq
    
    # Take lowest
    levels.append(('2T2g', min(E_2T2g_G, E_2T2g_H, E_2T2g_D, E_2T2g_F)))
    
    # 2A1g from 2S
    E_2A1g = E_2S
    levels.append(('2A1g', E_2A1g))
    
    # 2A2g from 2F
    E_2A2g = E_2F + 5*Dq
    levels.append(('2A2g', E_2A2g))
    
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
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.2f}")
print("="*60)

results = []
for Dq_over_B in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
    levels = tanabe_sugano_d7(Dq_over_B, B=1.0, C_over_B=C_over_B)
    results.append((Dq_over_B, levels))
    print(f"\nDq/B = {Dq_over_B}:")
    for i, (label, E_over_B) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {E_over_B:.4f}")

# Create plot
plt.figure(figsize=(10, 8))

# Collect all levels for plotting
all_levels = {i: [] for i in range(6)}
Dq_values = []

for Dq_over_B, levels in results:
    Dq_values.append(Dq_over_B)
    for i, (label, E_over_B) in enumerate(levels):
        all_levels[i].append(E_over_B)

# Plot each level
colors = ['blue', 'green', 'red', 'cyan', 'magenta', 'orange']
for i in range(6):
    plt.plot(Dq_values, all_levels[i], 'o-', color=colors[i], label=f'Level {i+1}')

plt.xlabel('Dq/B')
plt.ylabel('E/B')
plt.title('Tanabe-Sugano Diagram for d⁷ Octahedral Ion\n(B = 859 cm⁻¹, C = 3660 cm⁻¹)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.xlim(-0.1, 4.1)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150)
print("\n\nPlot saved as diagram.png")

