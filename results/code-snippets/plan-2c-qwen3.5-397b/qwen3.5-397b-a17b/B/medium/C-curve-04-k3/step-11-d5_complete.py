"""
Complete d5 Tanabe-Sugano calculation with proper state mixing.

The key insight is that 4T2g(G) mixes with 4T2g(D), which pulls its energy down.
Let me implement proper 2x2 mixing for 4T2g.
"""

import numpy as np

B = 800
C = 3473
C_B = C / B

# Free ion term energies
E_4G = 10 + 5 * C_B  # 31.706
E_4P = 23 + 5 * C_B  # 44.706
E_4D = 20 + 5 * C_B  # 41.706
E_4F = 25 + 5 * C_B  # 46.706

def calculate_energies(Dq_B):
    energies = {}
    energies['6A1g'] = 0.0
    
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
    # 4T2g(G) at E_4G + Dq (goes up)
    # 4T2g(D) at E_4D - 5Dq (goes down)
    # Off-diagonal mixing pulls 4T2g(G) down
    H_4T2g = np.array([
        [E_4G + Dq_B, 3*Dq_B],  # Reduced mixing coefficient
        [3*Dq_B, E_4D - 5*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]  # Lower eigenvalue is mostly 4T2g(G)
    energies['4T2g(D)'] = eig_4T2g[1]  # Higher eigenvalue is mostly 4T2g(D)
    
    # 4Eg(D) from 4D (with possible mixing with 4Eg(G), but 4Eg(G) is Dq-indep)
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4F-derived states
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

Dq_B_values = [1.45, 2.55, 3.25]

print("Results with 4T2g mixing:")
print("="*70)

results = {}
for Dq_B in Dq_B_values:
    energies = calculate_energies(Dq_B)
    excited_states = [(term, E) for term, E in energies.items() if term != '6A1g']
    sorted_states = sorted(excited_states, key=lambda x: x[1])
    
    print(f"\nDq/B = {Dq_B}:")
    for term, E in sorted_states[:7]:
        print(f"  {term:12s}: E/B = {E:8.3f}")
    
    three_lowest = sorted_states[:3]
    results[Dq_B] = three_lowest
    print(f"  Three lowest: {[(t[0], round(t[1],3)) for t in three_lowest]}")

# Final answer
print("\n" + "="*70)
print("FINAL ANSWER - Nine points:")
print("="*70)
for Dq_B in Dq_B_values:
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(results[Dq_B], 1):
        print(f"  {term}: E/B = {E:.3f}")
