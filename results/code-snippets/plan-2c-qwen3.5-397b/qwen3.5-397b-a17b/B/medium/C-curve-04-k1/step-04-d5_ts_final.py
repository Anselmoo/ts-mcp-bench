"""
Calculate d5 Tanabe-Sugano energies using proper reference.

The key insight: In Tanabe-Sugano diagrams, ALL energies are measured
relative to the ground state (6A1g for high-spin d5), and the ground
state energy itself may depend on Dq.

For d5 high-spin (t2g^3 eg^2):
- Ground state 6A1g from 6S
- E(6A1g) relative to barycenter = E(6S) + LF(6A1g)
- LF(6A1g) = 3*(-4Dq) + 2*(6Dq) = 0

So the ground state is at E = E(6S) = 0 (our reference).

For excited states, we need E(excited) - E(6A1g).

The free ion term energies relative to 6S are:
- 4G: 10B
- 4P: 23B
- 4D: 15B
- 4F: 5B
- 2I: 6B + 2C
- 2H, 2G: 10B + 2C
- etc.

But in the T-S diagram, we also need to account for the ligand field
stabilization of each state.

Let me use the standard T-S diagram matrices properly.
"""

import numpy as np

def d5_ts_energies(Dq_B, C_B=4.34125):
    """
    Calculate d5 term energies relative to 6A1g ground state.
    Using proper Tanabe-Sugano formalism.
    """
    
    # Free ion term energies relative to 6S (in units of B):
    # From Racah theory (C cancels for quartets):
    E_4G = 10.0
    E_4P = 23.0
    E_4D = 15.0
    E_4F = 5.0
    
    # Doublets (include C):
    E_2I = 6.0 + 2.0 * C_B
    E_2H = 10.0 + 2.0 * C_B
    E_2G = 10.0 + 2.0 * C_B
    E_2F = 13.0 + 2.0 * C_B
    
    energies = {}
    
    # Ground state: 6A1g at E = 0
    energies['6A1g'] = 0.0
    
    # === Quartet states ===
    
    # 4T1g from 4G and 4P (mixing):
    # The matrix in T-S formalism:
    # | E(4G) + LF_4T1g(G)    mixing |
    # | mixing                  E(4P) + LF_4T1g(P) |
    #
    # For 4T1g, the LF shifts are:
    # From 4G: -6Dq (this is the shift relative to 4G barycenter)
    # From 4P: -6Dq
    # But wait, we need to be careful about the reference.
    
    # Actually, in T-S diagrams, the energies are:
    # E(4T1g from 4G) = E(4G) - E(6S) + delta_LF
    # where delta_LF is the LF stabilization relative to the ground state.
    
    # For the ground state 6A1g (t2g^3 eg^2): LF = 0
    # For 4T1g from 4G (which has t2g^4 eg^1 character): LF = 4*(-4Dq) + 1*(6Dq) = -10Dq
    # So E(4T1g) relative to 6A1g = E(4G) - E(6S) + (-10Dq - 0) = 10B - 10Dq
    # In units of B: E/B = 10 - 10*(Dq/B)
    
    # Hmm, but this doesn't match T-S diagrams either. Let me reconsider.
    
    # The issue is that the 4G term doesn't correspond to a single configuration.
    # The 4G term has contributions from multiple configurations.
    
    # Let me use the standard T-S matrix elements directly:
    # From Tanabe-Sugano's original paper and subsequent work:
    
    # For d5 4T1g (G-P mixing):
    # Matrix (all in units of B):
    # | 10 - 6*Dq_B      4*Dq_B        |
    # | 4*Dq_B           23 - 6*Dq_B   |
    
    # Wait, I used this before and got negative energies. The issue is that
    # at Dq_B = 1.45: 10 - 6*1.45 = 10 - 8.7 = 1.3
    # And the eigenvalue would be even lower due to mixing.
    
    # But in actual T-S diagrams, 4T1g(G) is around E/B = 18-20 at Dq/B = 1.45.
    # So clearly my formula is wrong.
    
    # Let me look at this differently. In the T-S diagram:
    # At Dq/B = 0: 4T1g(G) should be at E/B = 10 (the 4G term energy)
    # As Dq/B increases, 4T1g(G) goes DOWN initially (stabilized by LF)
    # But it should stay positive (above ground state).
    
    # Actually, I think I've been confusing the LF shift conventions.
    # Let me look at the actual T-S diagram behavior:
    
    # For d5, from standard diagrams:
    # At Dq/B = 0:
    #   4G at E/B = 10
    #   4D at E/B = 15
    #   4P at E/B = 23
    #   4F at E/B = 5
    #
    # As Dq/B increases:
    #   4T1g(G) decreases from 10
    #   4T2g(G) increases from 10
    #   4A1g(G), 4Eg(G) stay at 10 (flat)
    #   4T1g(P) decreases from 23
    #   etc.
    
    # At Dq/B = 1.0, from typical diagrams:
    #   4T1g(G) ≈ 8-10
    #   4T2g(G) ≈ 12-14
    #   4A1g,4Eg(G) = 10
    #   4T1g(P) ≈ 18-20
    
    # At Dq/B = 2.0:
    #   4T1g(G) ≈ 5-7
    #   4T2g(G) ≈ 15-17
    #   4A1g,4Eg(G) = 10
    #   4T1g(P) ≈ 15-17
    
    # At Dq/B = 3.0:
    #   4T1g(G) ≈ 2-4
    #   4T2g(G) ≈ 18-20
    #   4A1g,4Eg(G) = 10
    #   4T1g(P) ≈ 12-14
    
    # So the 4T1g(G) does go down with increasing Dq/B, but stays positive
    # in the high-spin region.
    
    # My matrix gave 4T1g(G) at E/B = -0.91 for Dq/B = 1.45, which is wrong.
    # The issue must be with my matrix elements.
    
    # Let me reconsider the LF shifts. For a term from configuration t2g^n eg^m:
    # LF energy = n*(-4Dq) + m*(6Dq)
    #
    # For 6A1g (t2g^3 eg^2): LF = 3*(-4) + 2*(6) = 0
    # For 4T1g from 4G: The 4G term comes from t2g^3 eg^2 (same as ground!)
    #   So LF should also be 0? But that can't be right because 4T1g does shift.
    #
    # Actually, the 4G term has contributions from multiple configurations,
    # and the LF splitting within 4G gives different shifts to different
    # components (4T1g, 4T2g, 4A1g, 4Eg).
    
    # From group theory and LF theory:
    # For 4G -> 4T1g + 4T2g + 4A1g + 4Eg in Oh:
    # The splitting pattern (relative to 4G barycenter):
    #   4T1g: -6Dq (or some coefficient times Dq)
    #   4T2g: +4Dq
    #   4A1g, 4Eg: 0 (on average, they're degenerate)
    #
    # But these shifts are relative to the 4G barycenter, not relative to 6A1g.
    # So E(4T1g) = E(4G) + (-6Dq) = 10B - 6Dq
    # Relative to 6A1g: E(4T1g) - E(6A1g) = (10B - 6Dq) - 0 = 10B - 6Dq
    # In units of B: E/B = 10 - 6*(Dq/B)
    #
    # At Dq/B = 1.45: E/B = 10 - 6*1.45 = 10 - 8.7 = 1.3
    #
    # But this is without mixing with 4T1g(P). With mixing, the lower
    # eigenvalue would be even lower, possibly negative.
    
    # Hmm, but T-S diagrams show 4T1g(G) at E/B ≈ 18-20 at Dq/B = 1.45.
    # There's clearly a discrepancy.
    
    # Wait! I think I've been using the wrong free ion term energies.
    # In the T-S diagram for d5, the energies include the C parameter!
    #
    # E(4G) relative to 6S = 10B + 5C (not just 10B)
    # With C/B = 4.34: E(4G)/B = 10 + 5*4.34 = 31.7
    #
    # Let me recalculate with this:
    
    E_4G_full = 10.0 + 5.0 * C_B  # ≈ 31.7
    E_4P_full = 23.0 + 5.0 * C_B  # ≈ 44.7
    E_4D_full = 15.0 + 5.0 * C_B  # ≈ 36.7
    E_4F_full = 5.0 + 5.0 * C_B   # ≈ 26.7
    
    # Now 4T1g matrix:
    H_4T1g = np.array([
        [E_4G_full - 6*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P_full - 6*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # 4T2g matrix (from 4G and 4D):
    H_4T2g = np.array([
        [E_4G_full + 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D_full - 2*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # 4T2g from 4F (no mixing):
    energies['4T2g(F)'] = E_4F_full - 6*Dq_B
    
    # 4A1g, 4Eg from 4G (flat):
    energies['4A1g(G)'] = E_4G_full
    energies['4Eg(G)'] = E_4G_full
    
    # 4Eg from 4D:
    energies['4Eg(D)'] = E_4D_full + 6*Dq_B
    
    # 4A2g from 4F:
    energies['4A2g(F)'] = E_4F_full - 12*Dq_B
    
    # === Doublet states ===
    # Using E(2I) = 6B + 7C (need to verify)
    # Actually for doublets, the C coefficient is different.
    # From Racah: E(2I) - E(6S) = 6B + 2C (as I had before)
    
    E_2I_full = 6.0 + 2.0 * C_B  # ≈ 14.68
    E_2H_full = 10.0 + 2.0 * C_B  # ≈ 18.68
    E_2G_full = 10.0 + 2.0 * C_B  # ≈ 18.68
    
    # 2T2g from 2I (lowest doublet):
    # LF shift for 2T2g from 2I: approximately +2Dq
    energies['2T2g(I)'] = E_2I_full + 2*Dq_B
    
    # 2Eg from 2I:
    energies['2Eg(I)'] = E_2I_full + 5*Dq_B
    
    # 2T1g from 2H:
    energies['2T1g(H)'] = E_2H_full - 3*Dq_B
    
    # 2A1g from 2H (flat):
    energies['2A1g(H)'] = E_2H_full
    
    # 2T2g from 2G:
    energies['2T2g(G)'] = E_2G_full + 2*Dq_B
    
    # 2Eg from 2G:
    energies['2Eg(G)'] = E_2G_full + 5*Dq_B
    
    # 2T1g from 2G:
    energies['2T1g(G)'] = E_2G_full - 3*Dq_B
    
    # 2A1g from 2G (flat):
    energies['2A1g(G)'] = E_2G_full
    
    # 2T1g from 2I:
    energies['2T1g(I)'] = E_2I_full - 3*Dq_B
    
    # 2Eg from 2H:
    energies['2Eg(H)'] = E_2H_full + 5*Dq_B
    
    return energies

# Calculate and display
print("d5 Tanabe-Sugano energies (E/B relative to 6A1g ground):")
print(f"C/B = 4.34125 (from B=800, C=3473)\n")

for Dq_B in [1.45, 2.55, 3.25]:
    print(f"\n{'='*60}")
    print(f"Dq/B = {Dq_B}")
    print('='*60)
    
    energies = d5_ts_energies(Dq_B)
    
    # Sort by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("\nAll terms (sorted by energy):")
    for term, E_B in sorted_terms:
        marker = " <-- GROUND" if E_B <= 0.01 and term == '6A1g' else ""
        print(f"  {term:12s}: E/B = {E_B:7.2f}{marker}")
    
    print("\nThree lowest EXCITED terms (excluding ground 6A1g):")
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g' and e > 0]
    for i, (term, E_B) in enumerate(excited[:3]):
        print(f"  {i+1}. {term:12s}: E/B = {E_B:7.2f}")
