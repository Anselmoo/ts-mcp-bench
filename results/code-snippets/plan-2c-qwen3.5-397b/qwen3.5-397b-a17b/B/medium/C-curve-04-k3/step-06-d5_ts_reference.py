"""
Compare with published Tanabe-Sugano diagram values for d5.

Looking at standard d5 Tanabe-Sugano diagrams (e.g., from Cotton & Wilkinson,
or online resources), at various Dq/B values:

At Dq/B = 1.0:
- 4T1g(G): E/B ≈ 26-27
- 4T2g(G): E/B ≈ 28-29
- 4A1g/4Eg(G): E/B ≈ 30-32 (Dq-independent)

At Dq/B = 2.0:
- 4T1g(G): E/B ≈ 18-20
- 4T2g(G): E/B ≈ 22-24
- 4A1g/4Eg(G): E/B ≈ 30-32

At Dq/B = 3.0:
- 4T1g(G): E/B ≈ 10-12
- 4T2g(G): E/B ≈ 18-20
- 4A1g/4Eg(G): E/B ≈ 30-32

My calculated values should be compared to these.

With C/B = 4.34:
E(4G)/B = 10 + 5*4.34 = 31.7

Let me verify my calculations match the expected behavior.
"""

import numpy as np

def d5_TS_final(Dq_B, C_B):
    """
    Final d5 Tanabe-Sugano calculation.
    """
    energies = {}
    energies['6A1g'] = 0.0
    
    E_4G = 10 + 5*C_B
    E_4P = 23 + 5*C_B
    E_4D = 15 + 5*C_B
    E_4F = 25 + 5*C_B
    
    # 4A1g(G) and 4Eg(G) - Dq independent
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # 4T1g(G) from 4G-4P mixing
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # 4T2g(G) from 4G-4D mixing
    H_4T2g = np.array([
        [E_4G + Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D - 5*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # 4Eg(D)
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4F-derived
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

# Test at reference Dq/B values
C_B = 3473/800
print(f"C/B = {C_B:.4f}")
print(f"E(4G)/B = {10 + 5*C_B:.2f}")
print()

# Check at Dq/B = 1.0, 2.0, 3.0 for comparison with standard TS diagrams
for Dq_B in [1.0, 2.0, 3.0]:
    energies = d5_TS_final(Dq_B, C_B)
    print(f"Dq/B = {Dq_B}:")
    print(f"  4T1g(G): {energies['4T1g(G)']:.2f}")
    print(f"  4T2g(G): {energies['4T2g(G)']:.2f}")
    print(f"  4A1g/4Eg(G): {energies['4A1g(G)']:.2f}")
    print()

# Now calculate for the requested values
print("="*60)
print("REQUESTED VALUES:")
print("="*60)

Dq_B_values = [1.45, 2.55, 3.25]
all_results = {}

for Dq_B in Dq_B_values:
    energies = d5_TS_final(Dq_B, C_B)
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    three_lowest = sorted_terms[:3]
    all_results[Dq_B] = three_lowest
    
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(three_lowest):
        print(f"  {i+1}. {term}: E/B = {E:.3f}")

# Format for structured output
print("\n" + "="*60)
print("STRUCTURED OUTPUT FORMAT:")
print("="*60)
points = []
for Dq_B in Dq_B_values:
    for i, (term, E) in enumerate(all_results[Dq_B]):
        points.append({'Dq_B': Dq_B, 'term': term, 'E_B': round(E, 3)})
        
for p in points:
    print(f"Dq/B = {p['Dq_B']}, Term = {p['term']}, E/B = {p['E_B']}")
