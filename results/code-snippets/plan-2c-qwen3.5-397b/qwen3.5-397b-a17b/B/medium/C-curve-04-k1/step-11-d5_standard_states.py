"""
d5 Tanabe-Sugano calculation focusing on standard excited states.

For d5 octahedral complexes, the relevant excited states are:
- From 4G: 4T1g, 4T2g, 4A1g, 4Eg
- From 4P: 4T1g (mixes with 4T1g from 4G)
- From 4D: 4Eg, 4T2g
- Doublets from 2I, 2H, 2G, etc.

The 4F-derived states are typically higher in energy and not among
the lowest excited states in the high-spin region.
"""

import numpy as np

B = 800.0
C = 3473.0
C_B = C / B  # 4.34125

print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_B:.4f}")
print()

def d5_energies_standard(Dq_B):
    """Calculate d5 term energies for standard excited states."""
    
    # Free ion energies (in units of B)
    # T-S convention: quartets include 5C
    E_4G = 10.0 + 5.0 * C_B  # 31.706
    E_4P = 23.0 + 5.0 * C_B  # 44.706
    E_4D = 15.0 + 5.0 * C_B  # 36.706
    
    # Doublets (2C from Racah)
    E_2I = 6.0 + 2.0 * C_B   # 14.683
    E_2H = 10.0 + 2.0 * C_B  # 18.683
    E_2G = 10.0 + 2.0 * C_B  # 18.683
    
    energies = {'6A1g': 0.0}
    
    # === 4T1g (4G-4P mixing) ===
    H = np.array([[E_4G - 6*Dq_B, 4*Dq_B],
                  [4*Dq_B, E_4P - 6*Dq_B]])
    eig = np.linalg.eigvalsh(H)
    energies['4T1g(G)'] = eig[0]
    energies['4T1g(P)'] = eig[1]
    
    # === 4T2g (4G-4D mixing) ===
    H = np.array([[E_4G + 4*Dq_B, 4*Dq_B],
                  [4*Dq_B, E_4D - 2*Dq_B]])
    eig = np.linalg.eigvalsh(H)
    energies['4T2g(G)'] = eig[0]
    energies['4T2g(D)'] = eig[1]
    
    # === 4A1g, 4Eg from 4G (flat, degenerate) ===
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # === 4Eg from 4D ===
    energies['4Eg(D)'] = E_4D + 6*Dq_B
    
    # === Doublet states ===
    # Using LF shifts that give reasonable T-S diagram behavior
    
    # From 2I (lowest doublet)
    energies['2T1g(I)'] = E_2I - 2*Dq_B
    energies['2T2g(I)'] = E_2I + 3*Dq_B
    energies['2Eg(I)'] = E_2I + 6*Dq_B
    energies['2A1g(I)'] = E_2I
    energies['2A2g(I)'] = E_2I
    
    # From 2H
    energies['2T1g(H)'] = E_2H - 2*Dq_B
    energies['2T2g(H)'] = E_2H + 3*Dq_B
    energies['2Eg(H)'] = E_2H + 6*Dq_B
    energies['2A1g(H)'] = E_2H
    energies['2A2g(H)'] = E_2H
    
    # From 2G
    energies['2T1g(G)'] = E_2G - 2*Dq_B
    energies['2T2g(G)'] = E_2G + 3*Dq_B
    energies['2Eg(G)'] = E_2G + 6*Dq_B
    energies['2A1g(G)'] = E_2G
    energies['2A2g(G)'] = E_2G
    
    return energies

# Calculate and display
print("="*70)
results = {}

for Dq_B in [1.45, 2.55, 3.25]:
    energies = d5_energies_standard(Dq_B)
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    # All terms
    print(f"Dq/B = {Dq_B}:")
    print("-"*50)
    print("All terms (sorted):")
    for term, E_B in sorted_terms[:12]:
        marker = " [GROUND]" if term == '6A1g' else ""
        print(f"  {term:12s}: E/B = {E_B:7.2f}{marker}")
    
    # Three lowest excited (positive energy)
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g' and e > 0]
    three_lowest = excited[:3]
    results[Dq_B] = three_lowest
    
    print("\nThree lowest EXCITED terms:")
    for i, (term, E_B) in enumerate(three_lowest, 1):
        print(f"  {i}. {term:12s}: E/B = {E_B:.2f}")
    print()

# Summary
print("="*70)
print("SUMMARY: Three lowest excited terms at each Dq/B")
print("="*70)
for Dq_B in [1.45, 2.55, 3.25]:
    print(f"\nDq/B = {Dq_B}:")
    for term, E_B in results[Dq_B]:
        print(f"  {term}: E/B = {E_B:.2f}")
