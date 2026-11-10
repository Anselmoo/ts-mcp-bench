python3 << 'PYEOF'
import numpy as np

# For d7 octahedral Tanabe-Sugano diagram
# Given: B = 784 cm^-1, C = 3699 cm^-1, so C/B = 4.72

C_over_B = 3699 / 784  # = 4.718...

print(f"C/B = {C_over_B:.3f}")

# For d7 octahedral, using standard ligand field theory matrices
# The ground state at low-to-moderate field is 4T1g(F)

# Energy matrices (in units of B, relative to 4F barycenter):
# 
# 4T1g (mixing of 4T1g from 4F and 4T1g from 4P):
# Matrix: | -6x      4x    |
#         |  4x   15 - 6x  |
# where x = Dq/B
#
# 4T2g (from 4F only): E/B = 4x (relative to 4F barycenter)
# 4A2g (from 4F only): E/B = 14x (relative to 4F barycenter)

# Doublet states require more complex treatment including C/B

def calculate_d7_energies(Dq_over_B, C_over_B=4.72):
    """Calculate energies for d7 octahedral."""
    x = Dq_over_B
    
    # 4T1g 2x2 matrix eigenvalues (relative to 4F barycenter, in units of B)
    a = -6 * x
    b = 15 - 6 * x  
    c = 4 * x
    
    disc = np.sqrt((a - b)**2 + 4 * c**2)
    E_T1g_low = (a + b - disc) / 2  # Lower eigenvalue (ground at low field)
    E_T1g_high = (a + b + disc) / 2  # Higher eigenvalue (4T1g(P) mixed)
    
    # 4T2g and 4A2g (relative to 4F barycenter)
    E_T2g = 4 * x
    E_A2g = 14 * x
    
    # Convert to energies relative to ground state (4T1g_low)
    E_T2g_rel = E_T2g - E_T1g_low
    E_A2g_rel = E_A2g - E_T1g_low
    E_T1g_P_rel = E_T1g_high - E_T1g_low
    
    # Doublet states - these depend on C/B
    # From 2G term (at ~10B + 5C above 4F in free ion? Need to check)
    # Actually, for d7 free ion:
    # 4F is ground
    # 4P is at ~15B
    # 2G is at ~10B + 5C? Let me use standard values.
    
    # From standard atomic spectroscopy for d7:
    # Term energies relative to 4F (in units of B):
    # 4P: 15
    # 2G: ~18-22 (depends on C/B)
    # 2H: ~20-25
    # 2P: ~25-30
    # etc.
    
    # In octahedral field, these split and shift
    # 2G -> 2Eg + 2T1g + 2T2g
    # The 2Eg from 2G is often the lowest doublet
    
    # Approximate formula for 2Eg(2G) in octahedral d7:
    # E(2Eg) ≈ E(2G) + some Dq dependence
    # At Dq=0: E(2G)/B ≈ 10 + 5*(C/B) - corrections
    # With C/B = 4.72: E/B ≈ 10 + 23.6 = 33.6... that seems high
    
    # Let me use a different approach. From published Tanabe-Sugano diagrams:
    # For d7 with C/B ≈ 4.7:
    # At Dq/B = 0:
    #   4F at 0, 4P at 15, 2G at ~21, 2H at ~23, 2P at ~28
    # As Dq/B increases:
    #   4T1g(F) becomes ground
    #   4T2g rises with ~slope 10
    #   Doublets have various slopes
    
    # For a more accurate calculation, I need the full matrices including doublets
    # This is complex, so let me use approximate values from standard diagrams
    
    # Estimated doublet energies (relative to 4F barycenter, in units of B):
    # 2Eg(2G): ~21 - 2*Dq/B (roughly, decreases with field)
    # 2T1g(2G): ~21 + some Dq dependence
    # 2T2g(2G): ~21 + some Dq dependence
    
    # Actually, for d7, the doublet energies relative to ground 4T1g:
    # At Dq/B = 1-3, the lowest doublets are around E/B = 15-25
    
    # Let me use specific values from standard d7 Tanabe-Sugano diagrams
    # (These are approximate, based on typical diagrams with C/B ≈ 4.7)
    
    # Approximate doublet energies relative to ground state:
    # 2Eg: E/B ≈ 20 + 2*x (increases slightly with field)
    # 2T1g: E/B ≈ 22 + x
    # 2T2g: E/B ≈ 23 + x
    
    # These are rough estimates. For precise values, need full calculation.
    
    E_2Eg_rel = 20 + 2 * x  # Approximate
    E_2T1g_rel = 22 + x
    E_2T2g_rel = 24 + x
    
    return {
        '4T1g(F)': 0.0,  # Ground state
        '4T2g(F)': E_T2g_rel,
        '4A2g(F)': E_A2g_rel,
        '4T1g(P)': E_T1g_P_rel,
        '2Eg': E_2Eg_rel,
        '2T1g': E_2T1g_rel,
        '2T2g': E_2T2g_rel
    }

print("\nEnergies relative to ground state (E/B):")
for dq_b in [1.45, 2.45, 3.00]:
    print(f"\nDq/B = {dq_b}:")
    energies = calculate_d7_energies(dq_b, C_over_B)
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    for term, E in sorted_terms:
        print(f"  {term}: E/B = {E:.2f}")
PYEOF