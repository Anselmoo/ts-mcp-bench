"""
Final d5 Tanabe-Sugano calculation with correct energy reference.

Key insight: In T-S diagrams for d5, the free ion term energies relative
to 6S include C dependence:
- E(4G) - E(6S) = 10B + 5C (not just 10B!)
- E(4P) - E(6S) = 23B + 5C
- E(4D) - E(6S) = 15B + 5C
- E(4F) - E(6S) = 5B + 5C

This is because the T-S diagram uses a different energy zero than
pure Racah theory.

With C/B = 4.34125:
- E(4G)/B = 10 + 5*4.34125 = 31.71
- E(4P)/B = 23 + 5*4.34125 = 44.71
- E(4D)/B = 15 + 5*4.34125 = 36.71
- E(4F)/B = 5 + 5*4.34125 = 26.71

For doublets:
- E(2I)/B = 6 + 7*4.34125 = 36.39 (using 7C coefficient)
- Actually, let me use: E(2I) - E(6S) = 6B + 7C (from some conventions)
  or E(2I) - E(6S) = 6B + 2C (from Racah)
  
Let me use the convention where doublets have 7C coefficient like quartets.
"""

import numpy as np

C_B = 3473.0 / 800.0  # 4.34125

# Free ion energies (with C dependence, in units of B):
E_4G = 10.0 + 5.0 * C_B   # 31.71
E_4P = 23.0 + 5.0 * C_B   # 44.71
E_4D = 15.0 + 5.0 * C_B   # 36.71
E_4F = 5.0 + 5.0 * C_B    # 26.71

# Doublets (using 7C coefficient to match quartets):
E_2I = 6.0 + 7.0 * C_B    # 36.39
E_2H = 10.0 + 7.0 * C_B   # 40.39
E_2G = 10.0 + 7.0 * C_B   # 40.39
E_2F = 13.0 + 7.0 * C_B   # 43.39

print(f"C/B = {C_B}")
print(f"Free ion term energies (E/B at Dq=0):")
print(f"  Quartets: 4G={E_4G:.2f}, 4P={E_4P:.2f}, 4D={E_4D:.2f}, 4F={E_4F:.2f}")
print(f"  Doublets: 2I={E_2I:.2f}, 2H={E_2H:.2f}, 2G={E_2G:.2f}, 2F={E_2F:.2f}")
print()

def d5_energies(Dq_B):
    energies = {}
    energies['6A1g'] = 0.0  # Ground state reference
    
    # === 4T1g from 4G and 4P ===
    H_4T1g = np.array([
        [E_4G - 6*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 6*Dq_B]
    ])
    eig = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig[0]
    energies['4T1g(P)'] = eig[1]
    
    # === 4T2g from 4G and 4D ===
    H_4T2g = np.array([
        [E_4G + 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D - 2*Dq_B]
    ])
    eig = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig[0]
    energies['4T2g(D)'] = eig[1]
    
    # === 4T2g from 4F ===
    energies['4T2g(F)'] = E_4F - 6*Dq_B
    
    # === 4A1g, 4Eg from 4G (flat) ===
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # === 4Eg from 4D ===
    energies['4Eg(D)'] = E_4D + 6*Dq_B
    
    # === 4A2g from 4F ===
    energies['4A2g(F)'] = E_4F - 12*Dq_B
    
    # === Doublets ===
    # 2T2g from 2I
    energies['2T2g(I)'] = E_2I + 3*Dq_B
    energies['2Eg(I)'] = E_2I + 6*Dq_B
    energies['2T1g(I)'] = E_2I - 3*Dq_B
    energies['2A1g(I)'] = E_2I
    
    # From 2H
    energies['2T2g(H)'] = E_2H + 3*Dq_B
    energies['2Eg(H)'] = E_2H + 6*Dq_B
    energies['2T1g(H)'] = E_2H - 3*Dq_B
    energies['2A1g(H)'] = E_2H
    
    # From 2G
    energies['2T2g(G)'] = E_2G + 3*Dq_B
    energies['2Eg(G)'] = E_2G + 6*Dq_B
    energies['2T1g(G)'] = E_2G - 3*Dq_B
    energies['2A1g(G)'] = E_2G
    
    return energies

# Calculate for each Dq/B
for Dq_B in [1.45, 2.55, 3.25]:
    print(f"\n{'='*70}")
    print(f"Dq/B = {Dq_B}")
    print('='*70)
    
    energies = d5_energies(Dq_B)
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("\nLowest energy terms:")
    for term, E_B in sorted_terms[:15]:
        marker = " [GROUND]" if term == '6A1g' else ""
        print(f"  {term:12s}: E/B = {E_B:7.2f}{marker}")
    
    # Three lowest excited (excluding ground)
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g']
    print(f"\nThree lowest EXCITED terms:")
    for i, (term, E_B) in enumerate(excited[:3]):
        print(f"  {i+1}. {term:12s}: E/B = {E_B:7.2f}")
