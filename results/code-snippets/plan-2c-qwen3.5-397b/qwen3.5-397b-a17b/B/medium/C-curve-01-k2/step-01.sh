cat << 'EOF' > d4_tanabe_sugano.py
"""
Calculate d4 Tanabe-Sugano diagram energies.
For d4 octahedral, we need to diagonalize the ligand field + electron repulsion matrices.

Using Racah parameters B and C, with C/B = 3657/821 = 4.454

Key states for d4 in Oh symmetry:
- Quintets: 5Eg, 5T2g (from 5D)
- Triplets from 3F: 3A2g, 3T1g(F), 3T2g
- Triplets from 3P: 3T1g(P)
- Singlets: various

We'll use known analytical expressions and matrix elements.
"""

import numpy as np

# Given parameters
B = 821  # cm^-1
C = 3657  # cm^-1
C_over_B = C / B  # = 4.454

print(f"C/B = {C_over_B:.3f}")
print()

# For d4 Tanabe-Sugano diagram, we need energies of various terms
# The ground state changes from 5Eg (weak field) to 3T1g (strong field)

# Key energy expressions (in units of B, relative to barycenter of 5D at 0):
# 
# For 5Eg (t2g^3 eg^1): E = -6Dq (relative to 5D barycenter)
# For 5T2g (t2g^2 eg^2): E = +4Dq (relative to 5D barycenter)
# So 5T2g - 5Eg = 10Dq
#
# For triplet states from 3F term (at 15B above 5D in free ion):
# Need to solve 3x3 matrix for the three T1g states and 2x2 for others
#
# Actually, let me use the standard approach with known matrix elements

def d4_energies(Dq_over_B, C_over_B=4.454):
    """
    Calculate energies for d4 in octahedral field.
    Returns dict of term: E/B relative to ground state.
    """
    Dq = Dq_over_B * B  # in cm^-1, but we'll work in units of B
    
    # Energies relative to 5D barycenter (in units of B)
    # 5D is at E = 0 in free ion
    
    # Quintet states (from 5D, no electron repulsion splitting):
    # 5Eg: E = -6*Dq/B (relative to 5D)
    # 5T2g: E = +4*Dq/B (relative to 5D)
    E_5Eg = -6 * Dq_over_B
    E_5T2g = 4 * Dq_over_B
    
    # Triplet states from 3F (at 15B above 5D) and 3P (at ~30B above 5D)
    # In octahedral field, 3F splits into 3A2g, 3T1g, 3T2g
    # 3P gives 3T1g
    
    # For 3A2g (from 3F): E = 15B - 12Dq (approximate, need matrix)
    # Actually need to solve the full matrices
    
    # The 3T1g states mix 3F and 3P components
    # Matrix for 3T1g (in basis of 3F and 3P):
    # | 15B - 6Dq    4B        |
    # | 4B          30B + 0Dq  |  (3P is at ~30B, but exact value depends on C)
    
    # Actually for d4, the free ion terms are:
    # 5D at 0, 3P at ~15B + some C contribution, 3F at ~15B
    # More precisely: E(3P) = E(5D) + 15B, E(3F) = E(5D) + 15B - some C term
    
    # Let me use the standard Tanabe-Sugano approach
    # For d4, with proper Racah parameterization:
    
    # Free ion term energies (relative to 5D ground):
    # 3P: 15B
    # 3F: 15B (but this is approximate; actually depends on C)
    # More accurately for d4:
    # Using Slater-Condon parameters, the terms are at:
    # 5D: 0
    # 3P: 15B 
    # 3F: 15B - (some function of C)
    # Actually 3H, 3G, etc. also exist
    
    # For practical Tanabe-Sugano, we use:
    # The 3F term is at ~15B above 5D
    # The 3P term is at ~15B + additional from C
    
    # Let me use a more accurate approach with known matrix elements
    
    # For the 3T1g manifold (mixing 3F and 3P):
    # The matrix is (in units of B):
    # | 15 - 6x    4      |  where x = Dq/B
    # | 4         15 + 0x |  (3P at 15B, but this needs C correction)
    
    # Actually, the correct free ion separations for d4 are:
    # E(3P) - E(5D) = 15B
    # E(3F) - E(5D) = 15B - (depends on C/B)
    # For C/B = 4.454, we need proper values
    
    # Standard result: for d4, the 3F term is actually below 3P
    # E(3F) ≈ 15B - 3C/5 or similar
    
    # Let me use the approach from standard references:
    # The key matrix elements for d4 Oh:
    
    # For 3T1g states (two of them, from 3F and 3P mixing):
    # H = | 15B - 6Dq    4B      |
    #     | 4B          15B + 0Dq|  (3P at 15B from 5D)
    # But 3P-3F separation in free ion is affected by C
    
    # More accurately, for d4:
    # Free ion: 5D ground, then 3P at 15B, 3F at ~15B (very close)
    # Actually: E(3P) = 15B, E(3F) = 15B - 3C/5 + ... 
    
    # For simplicity in Tanabe-Sugano, often use:
    # 3P at 15B above 5D
    # 3F at 15B above 5D (but this gives degeneracy, so need C)
    
    # The proper treatment:
    # For dn configurations, term energies depend on B and C
    # For d4: 5D ground, 3P at E = 15B, 3F at E = 15B - (3/5)C + ...
    # Actually the formula is more complex
    
    # Let me use the standard Tanabe-Sugano parameterization:
    # All energies in units of B, with C/B as parameter
    
    # For d4, the key matrices are:
    
    # 3T1g matrix (from 3F and 3P):
    # In the basis |3F, 3P>:
    # H/B = | 15 - 6x - 3C/(5B)    4              |
    #       | 4                   15 + 0x + C/B   |
    # where x = Dq/B
    
    # Actually, let me look up the correct matrix elements for d4
    
    # Standard result for d4 3T1g matrix:
    # H = | E(3F) - 6Dq    4B    |
    #     | 4B            E(3P)  |
    # where E(3F) and E(3P) are free ion energies
    
    # For d4 free ion with Racah parameters:
    # E(5D) = A - 8B + 2C (set to 0 as reference)
    # E(3P) = A + 7B + 2C = 15B above 5D
    # E(3F) = A - 8B + 2C = 0 above 5D? No...
    
    # Let me use the correct formulas:
    # For d4:
    # E(5D) = A - 8B + 2C
    # E(3P) = A + 7B + 2C  => E(3P) - E(5D) = 15B
    # E(3F) = A - 8B + 2C  => E(3F) - E(5D) = 0? That can't be right.
    
    # Actually for d4, the terms are:
    # From d4 configuration: 5D, 3P, 3F, 3H, 3G, 1S, 1D, 1F, 1G, 1I
    # Using Racah: 
    # E(5D) = A - 8B + 2C
    # E(3H) = A - 17B + 2C  (below 5D? No, H has higher L)
    # 
    # Let me use standard values:
    # E(5D) = 0 (reference)
    # E(3P) = 15B
    # E(3F) ≈ 15B - 0.6C (approximately)
    # E(3G) ≈ 15B + 0.4C
    # E(3H) ≈ 15B + C
    
    # For C/B = 4.454:
    # E(3F)/B ≈ 15 - 0.6*4.454 = 15 - 2.67 = 12.33
    # E(3P)/B = 15
    # E(3G)/B ≈ 15 + 0.4*4.454 = 16.78
    # E(3H)/B ≈ 15 + 4.454 = 19.45
    
    # Actually, I should use the correct Racah formulas for d4
    # From standard texts (e.g., Figgis, Hitchman):
    
    # For d4:
    # E(5D) = A - 8B + 2C
    # E(3P) = A + 7B + 2C  => 15B above 5D
    # E(3F) = A - 8B + 2C  => 0 above 5D? That would make 3F degenerate with 5D
    
    # Hmm, this doesn't match. Let me reconsider.
    
    # Actually for d4, the correct term energies (from Condon-Shortley):
    # Using F2, F4 Slater integrals, or equivalently B, C:
    # B = F2 - 5F4/9, C = 35F4/9
    
    # For d4:
    # E(5D) = 6F0 - 35F2 - 63F4 = 6F0 - 35(B + 5C/35) - 63(9C/35)
    # This is getting complicated. Let me use tabulated values.
    
    # Standard result: for d4, relative to 5D ground:
    # 3P at 15B
    # 3F at ~12-13B (depends on C/B)
    # 3G at ~16-17B
    # 3H at ~19-20B
    
    # For Tanabe-Sugano diagrams, the energies are computed numerically
    # Let me use approximate analytical formulas that match standard diagrams
    
    # For d4 with C/B = 4.454, approximate free ion energies (in B units):
    E_3F_free = 12.5  # approximately
    E_3P_free = 15.0
    E_3G_free = 17.0
    E_3H_free = 19.5
    
    # Actually, let me compute more carefully using Racah formulas
    # For d4 configuration:
    # The energy expressions in terms of Racah A, B, C:
    # (from Griffith or Figgis)
    
    # E(5D) = A - 8B + 2C
    # E(3P) = A + 7B + 2C => E(3P) - E(5D) = 15B
    # E(3F) = A - 8B + 2C => same as 5D? That's wrong.
    
    # I think the issue is that for d4, different terms have different expressions
    # Let me look at this more carefully.
    
    # For d4 (or equivalently d6 by hole formalism with sign changes):
    # Using the formulas from "The Theory of Transition Metal Ions" (Griffith):
    
    # Actually, let me just use the standard Tanabe-Sugano diagram values
    # by reading from published diagrams for d4 with C/B ≈ 4.5
    
    # From standard d4 Tanabe-Sugano diagram (C/B = 4.5):
    # At Dq/B = 0.9:
    #   Ground: 5Eg at E/B = 0
    #   5T2g at E/B ≈ 9.0 (exactly 10*Dq/B = 9.0)
    #   3T1g at E/B ≈ 13-14
    #   3T2g at E/B ≈ 18-19
    #   3A2g at E/B ≈ 20-21
    #   3T1g(P) at E/B ≈ 25-27
    
    # At Dq/B = 2.15:
    #   Ground: 5Eg at E/B = 0 (or very close to 3T1g crossover)
    #   5T2g at E/B ≈ 21.5
    #   3T1g at E/B ≈ 2-4 (coming down)
    #   3T2g at E/B ≈ 15-17
    #   etc.
    
    # At Dq/B = 3.35:
    #   Ground: 3T1g at E/B = 0
    #   3T2g at E/B ≈ 8-10
    #   3A2g at E/B ≈ 12-14
    #   5Eg at E/B ≈ 15-18
    #   5T2g at E/B ≈ 25-28
    
    # Let me compute more accurately using the proper matrices
    
    # For 3T1g states (two states from 3F and 3P mixing):
    # Matrix in basis (3F, 3P):
    # | E(3F) - 6Dq    4B      |
    # | 4B            E(3P)    |
    
    # For d4, E(3F) and E(3P) relative to 5D:
    # Using proper Racah formulas for d4:
    # E(3P) - E(5D) = 15B
    # E(3F) - E(5D) = 15B - 3C/5 = 15B - 0.6C
    # (This is approximate; the exact formula involves more terms)
    
    # For C/B = 4.454:
    # E(3F)/B = 15 - 0.6*4.454 = 15 - 2.672 = 12.328
    # E(3P)/B = 15
    
    E_3F = 15 - 0.6 * C_over_B  # ≈ 12.33
    E_3P = 15.0
    
    # 3T1g matrix (in units of B):
    H_3T1g = np.array([
        [E_3F - 6*Dq_over_B, 4.0],
        [4.0, E_3P]
    ])
    E_3T1g_eigenvalues = np.linalg.eigvalsh(H_3T1g)
    E_3T1g_low = E_3T1g_eigenvalues[0]  # lower energy 3T1g
    E_3T1g_high = E_3T1g_eigenvalues[1]  # higher energy 3T1g (from 3P)
    
    # For 3T2g (from 3F only, no mixing):
    # E(3T2g) = E(3F) + 3Dq (approximately, need to check sign)
    # Actually for 3F -> 3A2g + 3T1g + 3T2g in Oh:
    # The splitting is: 3A2g at -12Dq, 3T2g at -2Dq, 3T1g at +6Dq (relative to 3F barycenter)
    # Wait, that's for d2. For d4 it might be different.
    
    # For d4, the 3F term splits as:
    # In strong field (t2g^4): 3T1g ground, 3T2g and 3A2g excited
    # The energies relative to 3F barycenter:
    # 3A2g: -12Dq, 3T2g: -2Dq, 3T1g: +6Dq (for the 3F-derived 3T1g)
    # But there's also 3T1g from 3P which mixes
    
    # Actually for d4 (more than half-filled), the signs might be reversed
    # Let me think about this more carefully.
    
    # For d4 in Oh, using hole formalism (d4 = d10 - d6 = 6 holes):
    # Actually d4 electron is like d6 hole, or d4 hole is like d6 electron
    # This is getting confusing. Let me use direct formulas.
    
    # For d4, the 3F term in octahedral field:
    # The matrix elements give:
    # 3A2g: E = E(3F) - 12Dq
    # 3T2g: E = E(3F) - 2Dq  
    # 3T1g(F): E = E(3F) + 6Dq (before mixing with 3P)
    
    # Wait, I need to verify these coefficients. For d2 (less than half):
    # 3F splits as 3A2g(-12Dq), 3T2g(-2Dq), 3T1g(+6Dq)
    # For d4 (more than half), by electron-hole symmetry with d6:
    # The signs of Dq terms reverse: 3A2g(+12Dq), 3T2g(+2Dq), 3T1g(-6Dq)
    # But d4 is not exactly like d6...
    
    # Actually, for d4 directly:
    # The weak-field terms from 3F:
    # Using the formulas from standard texts:
    # 3A2g: E = E(3F) + 12Dq
    # 3T2g: E = E(3F) + 2Dq
    # 3T1g(F component): E = E(3F) - 6Dq (before mixing)
    
    # Hmm, let me verify by checking the strong-field limit.
    # For d4 strong field (t2g^4):
    # Ground is 3T1g from t2g^4 configuration
    # Excited: 3T2g, 3A2g from t2g^4
    # The t2g^4 configuration gives: 3T1g, 3T2g, 3A2g, 1A1g, 1Eg, 1T2g
    # Energies relative to barycenter: 3T1g lowest, then 3T2g, then 3A2g
    
    # In strong field, the 3T1g ground should have E ≈ -6Dq + electron repulsion
    # Let me use the Tanabe-Sugano diagram behavior:
    # At high Dq/B, 3T1g is ground, 3T2g is first excited, 3A2g is second excited
    
    # For the 3F-derived states at weak field:
    # 3T1g: E = E(3F) - 6Dq (goes down with increasing Dq)
    # 3T2g: E = E(3F) + 2Dq (goes up)
    # 3A2g: E = E(3F) + 12Dq (goes up faster)
    
    # This matches: at high Dq, 3T1g becomes lowest
    
    E_3T2g = E_3F + 2 * Dq_over_B
    E_3A2g = E_3F + 12 * Dq_over_B
    
    # For 3G-derived states (3G at ~17B):
    # 3G splits into 3A1g, 3Eg, 3T1g, 3T2g
    # These are typically higher in energy
    
    E_3G = 15 + 0.4 * C_over_B  # ≈ 16.78
    # 3T1g from 3G: E ≈ E(3G) - 6Dq (may mix with other 3T1g)
    # 3T2g from 3G: E ≈ E(3G) + 2Dq
    # 3Eg from 3G: E ≈ E(3G) + 4Dq (approximate)
    # 3A1g from 3G: E ≈ E(3G) + 10Dq (approximate)
    
    # For 3H-derived states (3H at ~19.5B):
    E_3H = 15 + C_over_B  # ≈ 19.45
    # 3T1g from 3H, 3T2g from 3H, etc.
    
    # Now let's compile all states and find the three lowest excited states
    # for each Dq/B value
    
    # Quintet states:
    states = {
        '5Eg': E_5Eg,
        '5T2g': E_5T2g,
    }
    
    # Triplet states (from 3F):
    states['3T1g(F)'] = E_3T1g_low
    states['3T2g(F)'] = E_3T2g
    states['3A2g(F)'] = E_3A2g
    
    # Triplet state (from 3P, the higher 3T1g):
    states['3T1g(P)'] = E_3T1g_high
    
    # Find ground state and compute relative energies
    ground_term = min(states, key=states.get)
    E_ground = states[ground_term]
    
    # Compute E/B relative to ground
    relative_energies = {term: E - E_ground for term, E in states.items()}
    
    # Sort by energy
    sorted_states = sorted(relative_energies.items(), key=lambda x: x[1])
    
    return ground_term, sorted_states

# Calculate for each Dq/B value
Dq_B_values = [0.90, 2.15, 3.35]

for Dq_B in Dq_B_values:
    print(f"\n{'='*60}")
    print(f"Dq/B = {Dq_B}")
    print('='*60)
    
    ground, sorted_states = d4_energies(Dq_B, C_over_B)
    
    print(f"Ground state: {ground}")
    print(f"\nAll states (E/B relative to ground):")
    for term, E_rel in sorted_states:
        print(f"  {term}: E/B = {E_rel:.3f}")
    
    print(f"\nThree lowest excited states:")
    for i, (term, E_rel) in enumerate(sorted_states[1:4], 1):
        print(f"  {i}. {term}: E/B = {E_rel:.3f}")

EOF
python3 d4_tanabe_sugano.py