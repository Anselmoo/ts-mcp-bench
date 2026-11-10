import numpy as np

# More accurate calculation for d7 octahedral Tanabe-Sugano diagram
# Using proper energy matrices from ligand field theory

B = 784.0
C = 3699.0
C_over_B = C / B  # = 4.718...

print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")

# For d7 octahedral, the key matrices are:
# 
# Quartet states from 4F and 4P:
# - 4T1g: 2x2 matrix (mixing of 4T1g from 4F and 4T1g from 4P)
# - 4T2g: non-degenerate (from 4F only)
# - 4A2g: non-degenerate (from 4F only)
#
# Doublet states from 2G, 2H, 2P, 2D, 2F:
# - These require larger matrices and depend on C/B

# Free ion term energies for d7 (relative to 4F, in units of B):
# From Racah theory:
# E(4P) = 15B
# E(2G) = 10B + 5C = 10 + 5*(C/B) in units of B
# E(2H) = 10B + 5C (degenerate with 2G in some approximations)
# E(2P) = 15B + 5C
# E(2D) = varies
# E(2F) = varies

# Actually, the correct formulas for d7 free ion terms (from 3d7 configuration):
# Using Racah parameters A, B, C (A is common to all terms, so we use B and C)
# 
# E(4F) = A - 8B (ground term, set to 0)
# E(4P) = A + 7B = 15B above 4F
# E(2G) = A - 3B + 2C = 5B + 2C above 4F
# E(2H) = A - 3B + 2C = 5B + 2C above 4F (same as 2G)
# E(2P) = A + 7B + 2C = 15B + 2C above 4F
# E(2D) = A + 3B + 2C = 11B + 2C above 4F (one of the 2D terms)
# E(2F) = A + 9B + 2C = 17B + 2C above 4F

# With C/B = 4.72:
# E(2G)/B = 5 + 2*4.72 = 14.44
# E(2H)/B = 14.44
# E(2P)/B = 15 + 2*4.72 = 24.44
# E(2D)/B = 11 + 2*4.72 = 20.44
# E(2F)/B = 17 + 2*4.72 = 26.44

# In octahedral field, these terms split:
# 2G -> 2Eg + 2T1g + 2T2g
# 2H -> 2T1g + 2T2g (in Oh, 2H splits differently)
# etc.

# The splitting within each term depends on Dq
# For 2G in octahedral field:
# The 2Eg, 2T1g, 2T2g components have different Dq dependencies

# For a more accurate treatment, I need the full matrices
# Let me use approximate formulas based on standard TS diagrams

def calculate_d7_full(Dq_over_B, C_over_B=4.72):
    """
    Calculate d7 octahedral energies using ligand field theory.
    Returns dict of term: E/B (relative to ground state).
    """
    x = Dq_over_B
    
    # === Quartet states ===
    
    # 4T1g matrix (2x2, mixing 4T1g(F) and 4T1g(P))
    # Matrix elements relative to 4F barycenter (in units of B):
    # H11 = -6x (4T1g from 4F)
    # H22 = 15 - 6x (4T1g from 4P, where 15 = E(4P)/B)
    # H12 = H21 = 4x (mixing matrix element)
    
    a = -6 * x
    b = 15 - 6 * x
    c = 4 * x
    
    disc = np.sqrt((a - b)**2 + 4 * c**2)
    E_T1g_low = (a + b - disc) / 2  # Ground state (mostly 4F character)
    E_T1g_high = (a + b + disc) / 2  # Excited 4T1g (mostly 4P character)
    
    # 4T2g (from 4F only)
    # Energy relative to 4F barycenter: need to determine
    # In the weak field limit for d7:
    # 4F splits as: 4T1g at -6Dq, 4T2g at +4Dq, 4A2g at +14Dq (relative to barycenter)
    # This gives: 4T2g - 4T1g = 10Dq, 4A2g - 4T2g = 10Dq
    E_T2g_bary = 4 * x  # relative to 4F barycenter
    E_A2g_bary = 14 * x  # relative to 4F barycenter
    
    # Convert to energies relative to ground state
    E_ground = E_T1g_low
    E_T2g_rel = E_T2g_bary - E_ground
    E_A2g_rel = E_A2g_bary - E_ground
    E_T1g_P_rel = E_T1g_high - E_ground
    
    # === Doublet states ===
    
    # Free ion doublet energies (relative to 4F, in units of B):
    E_2G = 5 + 2 * C_over_B  # = 5 + 2*4.72 = 14.44
    E_2H = 5 + 2 * C_over_B  # same as 2G
    E_2D = 11 + 2 * C_over_B  # = 11 + 9.44 = 20.44
    E_2P = 15 + 2 * C_over_B  # = 15 + 9.44 = 24.44
    E_2F = 17 + 2 * C_over_B  # = 17 + 9.44 = 26.44
    
    # In octahedral field, these split with Dq dependence
    # For 2G -> 2Eg + 2T1g + 2T2g:
    # The splitting pattern and Dq dependence is complex
    # Approximate formulas (from standard references):
    
    # 2Eg from 2G: E ≈ E(2G) - 2*Dq (decreases with field)
    # 2T1g from 2G: E ≈ E(2G) + Dq (increases with field)
    # 2T2g from 2G: E ≈ E(2G) + Dq (increases with field)
    
    # 2T1g from 2H: E ≈ E(2H) + some Dq dependence
    # 2T2g from 2H: E ≈ E(2H) + some Dq dependence
    
    # 2D splits into 2Eg + 2T2g
    # 2P splits into 2T1g
    # 2F splits into 2T1g + 2T2g
    
    # For the lowest doublets, the main contributors are from 2G and 2D
    # Let me calculate approximate energies:
    
    # 2Eg (mainly from 2G): 
    E_2Eg_bary = E_2G - 2 * x  # decreases with field
    E_2Eg_rel = E_2Eg_bary - E_ground
    
    # 2T1g (from 2G and 2H mixing):
    E_2T1g_bary = E_2G + x  # increases with field
    E_2T1g_rel = E_2T1g_bary - E_ground
    
    # 2T2g (from 2G and 2H mixing):
    E_2T2g_bary = E_2G + x  # increases with field
    E_2T2g_rel = E_2T2g_bary - E_ground
    
    # There's also 2Eg from 2D at higher energy:
    E_2Eg_2D_bary = E_2D - 2 * x
    E_2Eg_2D_rel = E_2Eg_2D_bary - E_ground
    
    # And 2T1g from 2P:
    E_2T1g_2P_bary = E_2P + x
    E_2T1g_2P_rel = E_2T1g_2P_bary - E_ground
    
    return {
        '4T1g(F)': 0.0,
        '4T2g(F)': E_T2g_rel,
        '4A2g(F)': E_A2g_rel,
        '4T1g(P)': E_T1g_P_rel,
        '2Eg(G)': E_2Eg_rel,
        '2T1g(G)': E_2T1g_rel,
        '2T2g(G)': E_2T2g_rel,
        '2Eg(D)': E_2Eg_2D_rel,
        '2T1g(P)': E_2T1g_2P_rel
    }

print("\n" + "="*60)
print("d7 Octahedral Tanabe-Sugano Energies (E/B relative to ground)")
print("="*60)

for dq_b in [1.45, 2.45, 3.00]:
    print(f"\nDq/B = {dq_b}:")
    energies = calculate_d7_full(dq_b, C_over_B)
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("  All terms (sorted by energy):")
    for term, E in sorted_terms:
        print(f"    {term:12s}: E/B = {E:6.2f}")
    
    print("  Three lowest excited states:")
    excited = [(t, E) for t, E in sorted_terms if E > 0.01]  # Exclude ground
    for i, (term, E) in enumerate(excited[:3], 1):
        print(f"    {i}. {term}: E/B = {E:.2f}")
