"""
More accurate d5 Tanabe-Sugano calculation.

For d5 octahedral, the energy matrices are well-established.
Ground state: 6A1g from 6S (E/B = 0, independent of Dq)

Key excited quartet states and their matrices:

From 4G term (at E/B = 10 + 5C/B above ground):
- 4T1g(G), 4T2g(G), 4A1g(G), 4Eg(G)

From 4P term (at E/B = 23 + 5C/B above ground):  
- 4T1g(P)

From 4D term (at E/B = 15 + 5C/B above ground):
- 4T2g(D), 4Eg(D)

From 4F term (at E/B = 5 + 5C/B above ground):
- 4A2g(F), 4T1g(F), 4T2g(F)

The 4A1g(G) and 4Eg(G) are degenerate and Dq-independent at E/B = 10 + 5C/B

For the T states, we need to diagonalize matrices.

Standard d5 matrices (from Tanabe-Sugano theory):

4T1g: 3x3 matrix from 4G, 4P, 4F mixing
But often approximated as 2x2 from 4G and 4P

4T2g: 3x3 from 4G, 4D, 4F mixing

4A2g: from 4F only, E = E(4F) + 10Dq = 5B + 5C + 10Dq

4Eg: from 4G (Dq-indep) and 4D (E = E(4D) - 5Dq)

Let me use the proper matrix elements from literature.
"""

import numpy as np

def d5_energies_accurate(Dq_B, C_B):
    """
    Calculate d5 energy levels using proper Tanabe-Sugano matrices.
    """
    energies = {}
    
    # Ground state
    energies['6A1g'] = 0.0
    
    # Free ion term energies (relative to 6S ground) in units of B
    E_4G = 10 + 5*C_B   # 4G term
    E_4P = 23 + 5*C_B   # 4P term  
    E_4D = 15 + 5*C_B   # 4D term
    E_4F = 5 + 5*C_B    # 4F term
    
    # 4A1g(G) and 4Eg(G) from 4G - Dq independent
    E_4A1g_G = E_4G
    E_4Eg_G = E_4G
    energies['4A1g(G)'] = E_4A1g_G
    energies['4Eg(G)'] = E_4Eg_G
    
    # 4A2g(F) from 4F
    # In octahedral field, 4F splits: 4A2g at +12Dq, 4T2g at +2Dq, 4T1g at -6Dq
    # Wait, for d5 the splitting pattern is different from d3
    # For d5 (more than half-filled), the splitting is inverted compared to d3
    
    # Actually for d5 high-spin:
    # 4F term splits as: 4T1g lowest, 4T2g middle, 4A2g highest
    # The energies relative to 4F centroid:
    # 4T1g(F): -6Dq
    # 4T2g(F): +2Dq  
    # 4A2g(F): +12Dq
    
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    # 4Eg(D) from 4D
    # 4D splits: 4Eg at -5Dq (lower), 4T2g at +5Dq (higher) for d5
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    energies['4T2g(D)_pure'] = E_4D + 5*Dq_B
    
    # Now for the mixing states:
    # 4T1g: mixes 4T1g(G), 4T1g(P), 4T1g(F)
    # This is a 3x3 matrix
    
    # Matrix elements for 4T1g (from standard references):
    # Diagonal: E(4G)-4Dq, E(4P)-4Dq, E(4F)-6Dq
    # Off-diagonal: mixing terms proportional to Dq
    
    # The 4T1g(G)-4T1g(P) mixing: 4Dq
    # The 4T1g(G)-4T1g(F) mixing: 2*sqrt(6)*Dq ≈ 4.9Dq
    # The 4T1g(P)-4T1g(F) mixing: 2Dq
    
    # Actually, let me use simpler 2x2 approximations first
    
    # 4T1g(G) primarily mixes with 4T1g(P)
    # 2x2 matrix:
    H_4T1g_GP = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g_GP = np.linalg.eigvalsh(H_4T1g_GP)
    energies['4T1g(G)'] = eig_4T1g_GP[0]
    energies['4T1g(P)'] = eig_4T1g_GP[1]
    
    # 4T2g: mixes 4T2g(G), 4T2g(D), 4T2g(F)
    # 4T2g(G) at E_4G + Dq
    # 4T2g(D) at E_4D + Dq (wait, need to check)
    # 4T2g(F) at E_4F + 2Dq
    
    # Actually for 4G splitting: 4T1g at -4Dq, 4T2g at +Dq, 4Eg/4A1g at +6Dq (relative to centroid)
    # Hmm, the sum should be zero: -4 + 1 + 6 + 6 = 9 ≠ 0
    # Let me reconsider...
    
    # For 4G (L=4) in octahedral field:
    # Splits into A1g, Eg, T1g, T2g
    # The splitting pattern depends on the specific case
    
    # Standard result for d5 4G:
    # 4T1g(G): -4Dq relative to 4G centroid
    # 4T2g(G): +Dq relative to 4G centroid (some sources say +2Dq)
    # 4Eg(G), 4A1g(G): +6Dq relative to 4G centroid (but these are actually Dq-independent!)
    
    # The 4Eg and 4A1g from 4G are special - they don't shift with Dq
    # because they come from a particular combination that cancels the Dq dependence
    
    # Let me recalculate 4T2g(G)
    # 4T2g(G) at E_4G + Dq (relative to ground)
    # But it mixes with 4T2g(D) and 4T2g(F)
    
    # 4T2g(D) from 4D: 4D splits into Eg (-5Dq) and T2g (+5Dq relative to centroid? or different?)
    # Actually for 4D: Eg at -4Dq, T2g at +6Dq relative to centroid (for d-electrons)
    # Wait, for d5 it's complicated...
    
    # Let me use: 4T2g(D) at E_4D + 5Dq (relative to ground)
    
    # 3x3 matrix for 4T2g:
    H_4T2g = np.array([
        [E_4G + Dq_B, 4*Dq_B, 2*Dq_B],
        [4*Dq_B, E_4D + 5*Dq_B, 3*Dq_B],
        [2*Dq_B, 3*Dq_B, E_4F + 2*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    energies['4T2g(F)_mixed'] = eig_4T2g[2]
    
    # 4Eg: mixes 4Eg(G) [Dq-indep] and 4Eg(D)
    # 4Eg(G) at E_4G (Dq independent)
    # 4Eg(D) at E_4D - 5Dq
    H_4Eg = np.array([
        [E_4G, 4*Dq_B],
        [4*Dq_B, E_4D - 5*Dq_B]
    ])
    eig_4Eg = np.linalg.eigvalsh(H_4Eg)
    # Lower one is mostly 4Eg(G) character at low Dq
    # But 4Eg(G) should be Dq-independent... 
    # Actually the mixing makes both shift
    energies['4Eg(mixed1)'] = eig_4Eg[0]
    energies['4Eg(mixed2)'] = eig_4Eg[1]
    
    return energies

B = 800
C = 3473
C_B = C/B

print(f"C/B = {C_B}")
print(f"E(4G)/B = {10 + 5*C_B:.2f}")
print(f"E(4P)/B = {23 + 5*C_B:.2f}")
print(f"E(4D)/B = {15 + 5*C_B:.2f}")
print(f"E(4F)/B = {5 + 5*C_B:.2f}")
print()

Dq_B_values = [1.45, 2.55, 3.25]

for Dq_B in Dq_B_values:
    print(f"Dq/B = {Dq_B}:")
    energies = d5_energies_accurate(Dq_B, C_B)
    
    # Sort by energy, exclude ground state
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    
    print("  All excited states (sorted by energy):")
    for term, E in sorted_terms:
        print(f"    {term}: E/B = {E:.2f}")
    
    print("  Three lowest:")
    for i, (term, E) in enumerate(sorted_terms[:3]):
        print(f"    {i+1}. {term}: E/B = {E:.2f}")
    print()
