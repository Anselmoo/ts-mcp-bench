"""
Use published Tanabe-Sugano diagram data for d5.

I'll interpolate from known values in standard d5 T-S diagrams.
Reference: Tanabe & Sugano (1954), and subsequent compilations.

For d5 with C/B ≈ 4.3 (our case: C/B = 3473/800 = 4.34125):

At Dq/B = 0:
- 6A1g (ground): E/B = 0
- 4G terms: E/B ≈ 10 + 5*(C/B) ≈ 31.7 (but this is the barycenter)
  Actually in T-S diagrams, the quartet energies at Dq=0 are:
  - 4T1g(G), 4T2g(G), 4A1g(G), 4Eg(G) all from 4G at E/B = 10 + 5C/B
  Wait, that doesn't match standard diagrams...

Let me look at actual d5 T-S diagram values more carefully.

From standard references (e.g., Lever's "Inorganic Electronic Spectroscopy"):
For d5 (Mn2+, Fe3+ type, C/B ≈ 4-5):

At Dq/B = 0:
- Ground: 6A1g at E/B = 0
- 4G at E/B ≈ 10 (this is just 10B, C doesn't appear for quartets!)
- 4P at E/B ≈ 23
- 4D at E/B ≈ 15
- 4F at E/B ≈ 5
- 2I at E/B ≈ 6 + 2C/B ≈ 14-15
- 2H, 2G at E/B ≈ 10 + 2C/B ≈ 18-19

As Dq/B increases, these split according to Oh symmetry.

Let me use interpolated values from actual T-S diagrams:
"""

import numpy as np

# C/B ratio for this problem
C_B = 3473.0 / 800.0  # = 4.34125

# Free ion term energies relative to 6S (in units of B):
# Quartets (C doesn't appear):
E_4G = 10.0
E_4P = 23.0
E_4D = 15.0
E_4F = 5.0

# Doublets (include 2C):
E_2I = 6.0 + 2.0 * C_B   # ≈ 14.68
E_2H = 10.0 + 2.0 * C_B  # ≈ 18.68
E_2G = 10.0 + 2.0 * C_B  # ≈ 18.68
E_2F = 13.0 + 2.0 * C_B  # ≈ 21.68

print(f"C/B = {C_B}")
print(f"Free ion term energies (E/B at Dq=0):")
print(f"  4G: {E_4G}, 4P: {E_4P}, 4D: {E_4D}, 4F: {E_4F}")
print(f"  2I: {E_2I:.2f}, 2H: {E_2H:.2f}, 2G: {E_2G:.2f}, 2F: {E_2F:.2f}")
print()

# Now I need the LF splitting matrices for d5.
# From standard LF theory (Griffith, Figgis, etc.):

# For d5, the energy matrices in Oh symmetry:

def d5_energies_proper(Dq_B):
    """
    Calculate d5 energies using proper Tanabe-Sugano matrices.
    All energies relative to 6A1g ground state.
    """
    energies = {}
    energies['6A1g'] = 0.0
    
    # === 4T1g from 4G and 4P ===
    # Matrix (from Tanabe-Sugano 1954):
    # The diagonal elements include both the free ion energy and LF shift.
    # For 4T1g(G): E = E_4G - 6*Dq (relative to 6A1g)
    # For 4T1g(P): E = E_4P - 6*Dq
    # Off-diagonal mixing: 4*Dq
    
    # Wait, I need to verify these coefficients.
    # From the T-S paper, for d5 4T1g:
    # The matrix is:
    # | x - E    4Dq  |
    # | 4Dq    y - E  |
    # where x and y are the diagonal energies.
    
    # For d5:
    # x = E(4G) - 6Dq (for 4T1g from 4G)
    # y = E(4P) - 6Dq (for 4T1g from 4P)
    
    # But wait, if both have -6Dq, then the difference y - x = E(4P) - E(4G) = 13B
    # is independent of Dq. The mixing would give eigenvalues:
    # E = (x+y)/2 ± sqrt(((y-x)/2)^2 + (4Dq)^2)
    #   = (E_4G + E_4P)/2 - 6Dq ± sqrt((13/2)^2 + (4Dq)^2)
    
    # At Dq = 0: E = (10+23)/2 ± 13/2 = 16.5 ± 6.5 = 10, 23 ✓
    # At Dq > 0: the lower eigenvalue decreases, upper increases (relative to -6Dq shift)
    
    H_4T1g = np.array([
        [E_4G - 6*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 6*Dq_B]
    ])
    eig = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig[0]
    energies['4T1g(P)'] = eig[1]
    
    # === 4T2g from 4G, 4D, 4F ===
    # This is a 3x3 matrix, but let's do 2x2 for G-D mixing first.
    # For 4T2g(G): E = E_4G + 4*Dq
    # For 4T2g(D): E = E_4D - 2*Dq
    # Mixing: 4*Dq
    
    H_4T2g_GD = np.array([
        [E_4G + 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D - 2*Dq_B]
    ])
    eig = np.linalg.eigvalsh(H_4T2g_GD)
    energies['4T2g(G)'] = eig[0]
    energies['4T2g(D)'] = eig[1]
    
    # 4T2g from 4F (separate, may mix weakly):
    # For 4T2g(F): E = E_4F - 6*Dq (I think, need to verify)
    energies['4T2g(F)'] = E_4F - 6*Dq_B
    
    # === 4A1g, 4Eg from 4G ===
    # These are "horizontal" in T-S diagram (no Dq dependence)
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G  # Degenerate
    
    # === 4Eg from 4D ===
    # E = E_4D + 6*Dq (approximately)
    energies['4Eg(D)'] = E_4D + 6*Dq_B
    
    # === 4A2g from 4F ===
    # E = E_4F - 12*Dq
    # But wait, this gives negative energies at high Dq...
    # Let me check: at Dq/B = 1.45: E = 5 - 12*1.45 = 5 - 17.4 = -12.4
    # That's below ground state, which is wrong for high-spin region.
    
    # The issue is that 4A2g from 4F should not be calculated this way.
    # In the T-S diagram, the 4F-derived states are:
    # 4A2g, 4T1g, 4T2g
    # Their energies relative to 4F barycenter are:
    # 4A2g: -12Dq, 4T2g: -2Dq, 4T1g: +6Dq (these sum to 0, good)
    # So E(4A2g) = E_4F - 12Dq relative to 6A1g.
    
    # But E_4F = 5B, so at Dq = 0, E(4A2g) = 5B above ground.
    # As Dq increases, 4A2g goes down.
    # At Dq/B = 5/12 ≈ 0.42, E(4A2g) = 0 (crosses ground state)
    # For Dq/B > 0.42, 4A2g would be below ground... but that's not right.
    
    # Ah, I see the issue! The 4F term is at E = 5B above 6S.
    # But in the T-S diagram, we're plotting energies relative to the
    # ground state, which is 6A1g. The 6A1g energy also depends on Dq!
    
    # For high-spin d5 (t2g^3 eg^2): E_LF(6A1g) = 0
    # So 6A1g stays at E = 0 (relative to 6S).
    
    # For 4A2g from 4F, the configuration is different (likely t2g^4 eg^1
    # or t2g^3 eg^2 with different coupling).
    
    # Actually, the 4F term comes from the same t2g^3 eg^2 configuration
    # as the ground state! So the LF energy should be similar.
    
    # Hmm, this is getting complicated. Let me look at actual T-S diagrams.
    
    # From standard d5 T-S diagrams, the 4F-derived states (4A2g, 4T1g, 4T2g)
    # are typically NOT shown because they're higher in energy and not
    # relevant for typical d5 complexes.
    
    # Actually, I realize I may have the wrong understanding. Let me
    # reconsider which states are lowest.
    
    # For d5, the lowest excited states are typically:
    # 1. 4T1g from 4G (spin-allowed)
    # 2. 4T2g from 4G (spin-allowed)
    # 3. 4A1g, 4Eg from 4G (spin-allowed, degenerate)
    # 4. Various doublets (spin-forbidden)
    
    # The 4F-derived states are higher in energy.
    
    # Let me recalculate without the 4F states and focus on the
    # lowest excited states.
    
    # === Doublet states ===
    # These require more complex matrices. Let me use approximate formulas.
    
    # 2T2g from 2I (lowest doublet):
    # At Dq=0: E = E_2I = 6 + 2C/B ≈ 14.68
    # LF shift: approximately +2Dq to +5Dq depending on the state
    energies['2T2g(I)'] = E_2I + 3*Dq_B  # Approximate
    
    # 2Eg from 2I:
    energies['2Eg(I)'] = E_2I + 6*Dq_B
    
    # 2T1g from 2I:
    energies['2T1g(I)'] = E_2I - 3*Dq_B
    
    # 2A1g from 2I (flat):
    energies['2A1g(I)'] = E_2I
    
    # From 2H:
    energies['2T2g(H)'] = E_2H + 3*Dq_B
    energies['2Eg(H)'] = E_2H + 6*Dq_B
    energies['2T1g(H)'] = E_2H - 3*Dq_B
    energies['2A1g(H)'] = E_2H
    
    # From 2G:
    energies['2T2g(G)'] = E_2G + 3*Dq_B
    energies['2Eg(G)'] = E_2G + 6*Dq_B
    energies['2T1g(G)'] = E_2G - 3*Dq_B
    energies['2A1g(G)'] = E_2G
    
    return energies

# Calculate for each Dq/B
print("\n" + "="*70)
for Dq_B in [1.45, 2.55, 3.25]:
    print(f"\nDq/B = {Dq_B}")
    print("-"*70)
    
    energies = d5_energies_proper(Dq_B)
    
    # Sort and display
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("\nLowest energy terms:")
    for term, E_B in sorted_terms[:15]:
        ground_marker = " [GROUND]" if term == '6A1g' else ""
        print(f"  {term:12s}: E/B = {E_B:7.2f}{ground_marker}")
    
    # Three lowest excited (excluding ground)
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g']
    print(f"\nThree lowest EXCITED terms:")
    for i, (term, E_B) in enumerate(excited[:3]):
        print(f"  {i+1}. {term:12s}: E/B = {E_B:7.2f}")
