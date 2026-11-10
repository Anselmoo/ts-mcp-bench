python3 << 'PYEOF'
import numpy as np

# Final calculation for d7 octahedral Tanabe-Sugano diagram
# Using proper energy matrices and including doublet states more accurately

B = 784.0
C = 3699.0
C_over_B = C / B

print(f"d7 Octahedral: B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")
print()

def d7_ts_energies(Dq_over_B, C_over_B=4.718):
    """
    Calculate d7 octahedral term energies using ligand field theory.
    Based on standard Tanabe-Sugano formalism.
    """
    x = Dq_over_B
    
    # === Quartet states ===
    
    # 4T1g 2x2 matrix (mixing 4T1g(F) and 4T1g(P))
    # Matrix relative to 4F barycenter (in units of B):
    a = -6 * x           # 4T1g(F) diagonal
    b = 15 - 6 * x       # 4T1g(P) diagonal (15B above 4F)
    c = 4 * x            # Off-diagonal mixing
    
    disc = np.sqrt((a - b)**2 + 4 * c**2)
    E_T1g_low = (a + b - disc) / 2   # Ground state
    E_T1g_high = (a + b + disc) / 2  # Excited 4T1g(P)
    
    # 4T2g and 4A2g from 4F (relative to 4F barycenter)
    E_T2g_bary = 4 * x
    E_A2g_bary = 14 * x
    
    # === Doublet states ===
    # Free ion energies relative to 4F (in units of B):
    # E(2G) = 5B + 2C = 5 + 2*(C/B)
    # E(2D) = 11B + 2C
    # E(2P) = 15B + 2C
    # E(2F) = 17B + 2C
    
    E_2G = 5 + 2 * C_over_B
    E_2D = 11 + 2 * C_over_B
    E_2P = 15 + 2 * C_over_B
    E_2F = 17 + 2 * C_over_B
    
    # In octahedral field, these split with Dq dependence
    # Using approximate formulas from ligand field theory:
    
    # 2G -> 2Eg + 2T1g + 2T2g
    # The 2Eg from 2G has negative Dq slope, 2T1g and 2T2g have positive slopes
    E_2Eg_G_bary = E_2G - 2 * x
    E_2T1g_G_bary = E_2G + x
    E_2T2g_G_bary = E_2G + x
    
    # 2D -> 2Eg + 2T2g
    E_2Eg_D_bary = E_2D - 2 * x
    E_2T2g_D_bary = E_2D + x
    
    # 2P -> 2T1g
    E_2T1g_P_bary = E_2P + x
    
    # 2F -> 2T1g + 2T2g
    E_2T1g_F_bary = E_2F + x
    E_2T2g_F_bary = E_2F + x
    
    # Convert all to energies relative to ground state (4T1g_low)
    E_ground = E_T1g_low
    
    energies = {
        '4T1g(F)': 0.0,
        '4T2g(F)': E_T2g_bary - E_ground,
        '4A2g(F)': E_A2g_bary - E_ground,
        '4T1g(P)': E_T1g_high - E_ground,
        '2Eg(G)': E_2Eg_G_bary - E_ground,
        '2T1g(G)': E_2T1g_G_bary - E_ground,
        '2T2g(G)': E_2T2g_G_bary - E_ground,
        '2Eg(D)': E_2Eg_D_bary - E_ground,
        '2T2g(D)': E_2T2g_D_bary - E_ground,
        '2T1g(P)': E_2T1g_P_bary - E_ground,
        '2T1g(F)': E_2T1g_F_bary - E_ground,
        '2T2g(F)': E_2T2g_F_bary - E_ground,
    }
    
    return energies

# Calculate for each Dq/B value
results = {}
for dq_b in [1.45, 2.45, 3.00]:
    energies = d7_ts_energies(dq_b, C_over_B)
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    # Get three lowest excited states (exclude ground)
    excited = [(t, E) for t, E in sorted_terms if E > 0.01]
    three_lowest = excited[:3]
    
    results[dq_b] = three_lowest
    
    print(f"Dq/B = {dq_b}:")
    print(f"  Ground state: 4T1g(F) at E/B = 0.00")
    print(f"  Three lowest excited states:")
    for i, (term, E) in enumerate(three_lowest, 1):
        print(f"    {i}. {term}: E/B = {E:.2f}")
    print()

# Format final answer
print("="*60)
print("FINAL ANSWER: Nine points (3 Dq/B values × 3 excited states each)")
print("="*60)

all_points = []
for dq_b in [1.45, 2.45, 3.00]:
    for term, E in results[dq_b]:
        all_points.append((dq_b, term, E))
        print(f"Dq/B = {dq_b:4.2f}: {term:10s} at E/B = {E:6.2f}")
PYEOF