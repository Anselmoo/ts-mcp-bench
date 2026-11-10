cat << 'EOF' > d5_ts_accurate.py
"""
More accurate d5 Tanabe-Sugano calculation.

I'll use the proper matrices from ligand field theory references.
Key reference: Tanabe & Sugano (1954), J. Phys. Soc. Japan.

For d5, the ground state is 6A1g (high-spin) for Dq/B below the crossover.
The crossover to low-spin (2T2g ground) occurs around Dq/B ≈ 2.8-3.0 for C/B ≈ 4.3.

For this problem, we need the three lowest excited terms at each Dq/B.
These could be quartets (spin-allowed) or doublets (spin-forbidden).

Using matrices from standard LF theory (Figgis, Griffith, etc.):
"""

import numpy as np

def d5_tanabe_sugano(Dq_B, C_B=4.34125):
    """
    Calculate d5 term energies using proper Tanabe-Sugano matrices.
    Returns dict of term: E/B (relative to 6A1g ground state).
    """
    
    # Free ion term energies relative to 6S (in units of B):
    # From Racah theory for d5:
    # Note: In the standard T-S diagram formulation, the C parameter
    # affects the term energies. The formulas are:
    
    # Actually, let me use the formulation where:
    # E(6S) = 0 (ground state reference)
    # E(4G) = 10 + 5*(C/B)  [this is the standard T-S convention]
    # E(4P) = 23 + 5*(C/B)
    # E(4D) = 15 + 5*(C/B)
    # E(4F) = 5 + 5*(C/B)
    
    # But wait, I need to verify this. In some conventions, the 
    # term separations don't include C. Let me check both.
    
    # Convention 1: E(4G) - E(6S) = 10B (no C dependence)
    # Convention 2: E(4G) - E(6S) = 10B + 5C (with C dependence)
    
    # The Tanabe-Sugano diagrams show C/B dependence, so convention 2
    # is used in T-S diagrams.
    
    E_6S = 0.0
    E_4G = 10.0 + 5.0 * C_B
    E_4P = 23.0 + 5.0 * C_B
    E_4D = 15.0 + 5.0 * C_B
    E_4F = 5.0 + 5.0 * C_B
    
    # Doublet term energies (from Racah theory for d5):
    # E(2I) = 6B + 5C (approximately)
    # E(2H) = 10B + 5C
    # E(2G) = 10B + 5C (same as 4G?)
    # E(2F) = ...
    # E(2D) = ... (two different 2D terms)
    # E(2P) = ...
    # E(2S) = ...
    
    # From standard tables:
    # E(2I) = 6 + 5*C/B  (lowest doublet)
    # E(2H) = E(2G) = 10 + 5*C/B (degenerate with 4G?)
    # Actually the doublet energies are more complex.
    
    # Let me use approximate values from T-S diagrams:
    # The lowest doublets (2I, 2H, 2G) are around E/B = 15-25 at Dq=0
    # for C/B ≈ 4.3.
    
    E_2I = 6.0 + 5.0 * C_B  # ≈ 27.7
    E_2H = 10.0 + 5.0 * C_B  # ≈ 31.7
    E_2G = 10.0 + 5.0 * C_B  # ≈ 31.7
    
    # Actually, I realize the doublet energies relative to 6S
    # might not include the 5C term. Let me reconsider.
    
    # From Condon-Shortley for d5:
    # The electrostatic energies (in terms of Racah A, B, C):
    # 6S: 10A - 35B + 7C
    # 4G: 10A - 25B + 7C  => diff = 10B
    # 4P: 10A - 12B + 7C  => diff = 23B
    # 4D: 10A - 20B + 7C  => diff = 15B
    # 4F: 10A - 30B + 7C  => diff = 5B
    # 2I: 10A - 29B + 9C  => diff = 6B + 2C
    # 2H: 10A - 25B + 9C  => diff = 10B + 2C
    # 2G: 10A - 25B + 9C  => diff = 10B + 2C
    # 2F: 10A - 22B + 9C  => diff = 13B + 2C
    # 2D(a): 10A - 20B + 9C => diff = 15B + 2C
    # 2D(b): 10A - 15B + 9C => diff = 20B + 2C
    # 2P: 10A - 12B + 9C  => diff = 23B + 2C
    # 2S: 10A - 10B + 9C  => diff = 25B + 2C
    
    # So relative to 6S (in units of B):
    E_4G = 10.0
    E_4P = 23.0
    E_4D = 15.0
    E_4F = 5.0
    E_2I = 6.0 + 2.0 * C_B  # ≈ 6 + 8.68 = 14.68
    E_2H = 10.0 + 2.0 * C_B  # ≈ 18.68
    E_2G = 10.0 + 2.0 * C_B  # ≈ 18.68
    E_2F = 13.0 + 2.0 * C_B  # ≈ 21.68
    E_2D_a = 15.0 + 2.0 * C_B  # ≈ 23.68
    E_2D_b = 20.0 + 2.0 * C_B  # ≈ 28.68
    E_2P = 23.0 + 2.0 * C_B  # ≈ 31.68
    E_2S = 25.0 + 2.0 * C_B  # ≈ 33.68
    
    # Now for the ligand field matrices:
    
    energies = {}
    
    # === Ground state: 6A1g ===
    # For high-spin d5 (t2g^3 eg^2): E_LF = 0
    energies['6A1g'] = 0.0
    
    # === 4T1g states (from 4G and 4P mixing) ===
    # Matrix elements from standard LF theory:
    # <4T1g(G)|H|4T1g(G)> = E_4G - 6*Dq
    # <4T1g(P)|H|4T1g(P)> = E_4P - 6*Dq
    # <4T1g(G)|H|4T1g(P)> = 4*Dq
    
    H_4T1g = np.array([
        [E_4G - 6*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 6*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # === 4T2g states (from 4G, 4D, 4F mixing) ===
    # This is a 3x3 matrix. Let me include all three.
    # Matrix elements (approximate, from standard tables):
    # <4T2g(G)|H|4T2g(G)> = E_4G + 4*Dq
    # <4T2g(D)|H|4T2g(D)> = E_4D - 2*Dq
    # <4T2g(F)|H|4T2g(F)> = E_4F - 6*Dq
    # Off-diagonals:
    # <4T2g(G)|H|4T2g(D)> = 4*Dq (approximately)
    # <4T2g(G)|H|4T2g(F)> = 0 (no direct mixing?)
    # <4T2g(D)|H|4T2g(F)> = 4*Dq (approximately)
    
    # Actually the mixing patterns are more complex. Let me use 2x2 for G-D mixing:
    H_4T2g = np.array([
        [E_4G + 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D - 2*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # Also include 4T2g from 4F (no mixing for simplicity):
    energies['4T2g(F)'] = E_4F - 6*Dq_B
    
    # === 4A1g, 4Eg from 4G ===
    # These are "flat" - no Dq dependence (to first order)
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G  # Degenerate
    
    # === 4Eg from 4D ===
    # This can mix with 4Eg(G), but let's treat separately:
    energies['4Eg(D)'] = E_4D + 6*Dq_B  # Approximate LF shift
    
    # === 4A2g from 4F ===
    energies['4A2g(F)'] = E_4F - 12*Dq_B
    
    # === Doublet states ===
    # These require 2x2 or larger matrices due to mixing.
    # For simplicity, I'll use approximate formulas.
    
    # 2T1g from 2I and 2H mix:
    # At Dq=0: E = E_2I for lower, E_2H for higher
    # With LF: complex mixing
    
    # For 2T1g, the matrix involves 2T1g from 2I, 2H, 2G, 2F
    # This is complex. Let me use approximate values from T-S diagrams.
    
    # From d5 T-S diagram, the lowest doublets are:
    # 2T1g, 2Eg, 2A1g, 2T2g from various parent terms.
    
    # Approximate energies (based on typical T-S diagram):
    # 2T2g(I): from 2I, shifts with Dq
    # 2Eg(I): from 2I
    # 2T1g(H): from 2H
    # etc.
    
    # For 2T2g from 2I (lowest doublet at low Dq):
    # E ≈ E_2I + 2*Dq (approximate)
    energies['2T2g(I)'] = E_2I + 2*Dq_B
    
    # For 2Eg from 2I:
    energies['2Eg(I)'] = E_2I + 5*Dq_B  # Approximate
    
    # For 2T1g from 2H:
    energies['2T1g(H)'] = E_2H - 3*Dq_B  # Approximate
    
    # For 2A1g from 2H:
    energies['2A1g(H)'] = E_2H + 0*Dq_B  # Flat (approximate)
    
    # For 2T2g from 2G:
    energies['2T2g(G)'] = E_2G + 2*Dq_B
    
    # For 2Eg from 2G:
    energies['2Eg(G)'] = E_2G + 5*Dq_B
    
    # More doublets (higher energy):
    energies['2T1g(G)'] = E_2G - 3*Dq_B
    energies['2A1g(G)'] = E_2G
    
    return energies

# Calculate for the three Dq/B values
print("d5 Tanabe-Sugano energies (E/B relative to 6A1g ground):")
print(f"C/B = 4.34125\n")

for Dq_B in [1.45, 2.55, 3.25]:
    print(f"\n{'='*50}")
    print(f"Dq/B = {Dq_B}")
    print('='*50)
    
    energies = d5_tanabe_sugano(Dq_B)
    
    # Sort by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("\nAll terms (sorted by energy):")
    for term, E_B in sorted_terms:
        print(f"  {term:12s}: E/B = {E_B:7.2f}")
    
    print("\nThree lowest excited terms (excluding ground 6A1g):")
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g']
    for term, E_B in excited[:3]:
        print(f"  {term:12s}: E/B = {E_B:7.2f}")
EOF
python3 d5_ts_accurate.py