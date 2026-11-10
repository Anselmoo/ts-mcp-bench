"""
Calculate d5 Tanabe-Sugano diagram energies.
For d5 octahedral, we need to diagonalize the ligand field matrices
for each symmetry term.

The free ion terms for d5 are: 6S, 4G, 4P, 4D, 4F, and various doublets.

In Oh symmetry:
- 6S -> 6A1g (ground state)
- 4G -> 4T1g, 4T2g, 4A1g, 4Eg
- 4P -> 4T1g
- 4D -> 4Eg, 4T2g
- 4F -> 4A2g, 4T1g, 4T2g

We use the matrices from standard ligand field theory references.
"""

import numpy as np

# Racah parameters
B = 800.0
C = 3473.0

# For d5, the energy matrices in units of B
# We'll use the standard Tanabe-Sugano formulation

def d5_energies(Dq_B):
    """
    Calculate energies for d5 octahedral complex.
    Returns dictionary of term: E/B values
    """
    Dq = Dq_B * B
    
    # Ground state: 6A1g from 6S
    # Energy of 6A1g is taken as zero (reference)
    # E(6A1g) = 0
    
    energies = {}
    
    # For d5 high-spin, the 6A1g is the ground state
    # The excited states come from various quartet and doublet terms
    
    # Using standard d5 Tanabe-Sugano diagram data
    # Energies are given relative to ground state in units of B
    
    # 4T1g(G) - from 4G term
    # Matrix element for 4T1g(G): E = 7.5B + 3Dq - sqrt((7.5B)^2 - 30B*Dq + 9Dq^2 + ...)
    # Actually need proper diagonalization
    
    # Let me use the standard formulas from Tanabe-Sugano diagrams
    
    # For 4T1g from 4G (lower energy 4T1g):
    # The 4G term splits, and we need to solve the secular determinant
    
    # Using standard reference data for d5:
    # At Dq/B = 0:
    # 4G is at 10B (actually E(4G) = 10B - 14C approximately, but in T-S diagram normalized)
    # Actually for d5: E(4G) = 10B + 5C relative to 6S... let me recalculate
    
    # Free ion term energies for d5 (relative to 6S ground):
    # E(4G) = 10B + 5C  (but this includes C)
    # In Tanabe-Sugano, energies are typically plotted as E/B vs Dq/B
    # with C/B fixed (usually C/B ≈ 4-5)
    
    # For proper calculation, I'll use the matrices from Griffith or similar
    
    # Simplified approach using known T-S diagram values:
    
    # 4T1g(G) - the lower 4T1g from 4G
    # Energy matrix involves mixing with 4T1g(P)
    
    # Let me use the actual Tanabe-Sugano calculation approach
    
    # For d5, the key matrices are:
    
    # 4T1g states (from 4G and 4P, they mix):
    # | 4T1g(G) > and | 4T1g(P) >
    # Matrix:
    # | -6Dq - E(4G)    4Dq           |
    # | 4Dq             10B - E(4P) - 6Dq |
    # This is approximate...
    
    # Let me use a more direct approach with published formulas
    
    # From standard texts (e.g., Figgis, "Introduction to Ligand Fields"):
    # For d5:
    
    # 4T1g(G) and 4T1g(P) mix. The matrix is:
    # [ -6Dq + 10B + 5C    4Dq          ]
    # [ 4Dq                15B + 5C - 6Dq ]
    # Wait, this needs careful treatment
    
    # Actually, for Tanabe-Sugano diagrams, the ground state 6A1g
    # has energy that depends on Dq too (for d5, 6A1g is from 6S which 
    # doesn't split, but its energy relative to barycenter does change)
    
    # Let me use the standard approach:
    # Ground state 6A1g energy: E = 0 (by convention in T-S diagrams)
    
    # For the excited states, I'll calculate using the proper matrices
    
    # 4T1g(G) - 4T1g(P) mixing matrix (energies relative to 6A1g):
    # The 4G term is at 10B + 5C above 6S
    # The 4P term is at 23B + 5C above 6S (approximately)
    
    # In the T-S diagram normalization, we use:
    # E(4G) = 10B (ignoring C for the moment, or C is absorbed)
    # Actually C/B ratio matters...
    
    # Let me use the actual calculation with C/B = 3473/800 = 4.34125
    
    CB_ratio = C / B  # ≈ 4.34
    
    # Free ion term energies (from 6S):
    E_4G = 10*B + 5*C   # 4G term energy
    E_4P = 23*B + 5*C   # 4P term energy (approximate)
    E_4D = 15*B + 5*C   # 4D term energy
    E_4F = 5*B          # 4F term energy (this is below 4G!)
    
    # Wait, I need to check the ordering. For d5:
    # Ground: 6S
    # Then: 4G, 4P, 4D, 4F... 
    # Actually 4F is lower than 4G in some conventions
    
    # Let me use the correct Racah formula for d5:
    # E(6S) = 0 (ground)
    # E(4G) = 10B + 5C
    # E(4P) = 23B + 5C  
    # E(4D) = 15B + 5C
    # E(4F) = 5B + 5C (actually this might be different)
    
    # Hmm, I need to be more careful. Let me use standard values.
    
    # From Condon-Shortley / Racah for d5:
    # Term energies relative to 6S:
    # 4G: 10B + 5C
    # 4P: 23B + 5C
    # 4D: 15B + 5C
    # 4F: 5B + 5C (but 4F doesn't exist for d5... wait)
    
    # Actually for d5, the terms are:
    # Sextet: 6S
    # Quartets: 4G, 4P, 4D, 4F
    # Doublets: many (2I, 2H, 2G, 2F, 2D, 2P, 2S)
    
    # Let me look up the actual energies:
    # E(4G) = 10B + 5C
    # E(4P) = 23B + 5C
    # E(4D) = 15B + 5C  
    # E(4F) = 5B + 5C - but I'm not sure about this
    
    # For the Tanabe-Sugano diagram, what matters is:
    # The ground state is 6A1g (from 6S)
    # Energies are measured from this ground state
    
    # In octahedral field:
    # 6S -> 6A1g (no splitting, but energy shifts with Dq)
    # For d5 high-spin t2g^3 eg^2: E = 3*(-4Dq) + 2*(6Dq) = 0
    # So 6A1g stays at E = 0
    
    # Now for excited quartets:
    
    # 4T1g from 4G: 
    # The 4G term (10B + 5C above 6S) splits in Oh field
    # For 4T1g(G): need to solve 2x2 matrix with 4T1g(P)
    
    # The matrix for 4T1g states (from 4G and 4P):
    # | E(4G) - 6Dq      4Dq           |
    # | 4Dq              E(4P) - 6Dq   |
    # 
    # Eigenvalues give the two 4T1g energies
    
    # But wait, the diagonal elements should be:
    # For 4T1g(G): the center of 4G is at E(4G), and in Oh field
    # the T1g component is shifted. The shift depends on the specific
    # matrix elements.
    
    # Let me use the standard formulation from Tanabe-Sugano papers:
    
    # For d5, using the matrices from "The Theory of Transition Metal Ions" (Griffith):
    
    # Actually, let me just use the published Tanabe-Sugano diagram values
    # by interpolation, which is more reliable.
    
    # From standard d5 Tanabe-Sugano diagram (C/B ≈ 4.34):
    
    # At Dq/B = 1.45:
    # Looking at the diagram, the lowest excited terms are typically:
    # 4T1g(G), 4T2g(G), 4A1g(G)/4Eg(G)
    
    # Let me calculate using proper matrices:
    
    # 4T1g(G) - 4T1g(P) mixing:
    # Matrix (relative to 6A1g ground):
    # H = | 10B+5C - 6Dq    4Dq        |
    #     | 4Dq             23B+5C - 6Dq |
    
    # Actually the off-diagonal is 4Dq for the mixing
    
    # Hmm, I realize I need the exact matrix elements. Let me use
    # a different approach - use published T-S diagram data.
    
    # From standard references for d5 with C/B ≈ 4.3:
    
    # I'll create a lookup/interpolation from known T-S diagram points
    
    # Known points from d5 Tanabe-Sugano (approximate, C/B = 4.34):
    # Dq/B = 0: 4G at 10 + 5*4.34 = 31.7, 4P at 23 + 5*4.34 = 44.7, etc.
    
    # At Dq/B = 1.0:
    # 4T1g(G) ≈ 20-22
    # 4T2g(G) ≈ 22-24
    # 4A1g,4Eg(G) ≈ 28-30 (flat, from 4G)
    # 4T1g(P) ≈ 35-40
    
    # At Dq/B = 2.0:
    # 4T1g(G) ≈ 15-18
    # 4T2g(G) ≈ 20-22
    # 4A1g,4Eg(G) ≈ 28-30
    # 4T1g(P) ≈ 30-35
    
    # This is getting complicated. Let me use a proper calculation.
    
    return energies

# Actually, let me use a different approach - read from a reference
# or calculate properly using the ligand field matrices

print("Need to calculate d5 Tanabe-Sugano energies properly")
print(f"C/B ratio = {C/B}")
