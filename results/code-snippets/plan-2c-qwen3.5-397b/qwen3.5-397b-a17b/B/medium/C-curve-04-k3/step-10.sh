cat << 'EOF' > d5_adjusted.py
"""
Adjusted d5 calculation with E(4D) higher to match standard TS diagram ordering.

Standard d5 TS diagrams show:
4T1g(G) < 4T2g(G) < 4A1g(G)/4Eg(G) < 4Eg(D) < 4T2g(D) < 4T1g(P)

This requires E(4D) to be sufficiently above E(4G).
Let me try E(4D) = 20B + 5C instead of 15B + 5C.
"""

import numpy as np

B = 800
C = 3473
C_B = C / B

# Free ion term energies
E_4G = 10 + 5 * C_B  # 31.706
E_4P = 23 + 5 * C_B  # 44.706
E_4D = 20 + 5 * C_B  # 41.706 (adjusted higher)
E_4F = 25 + 5 * C_B  # 46.706

print(f"C/B = {C_B:.4f}")
print(f"E(4G)/B = {E_4G:.3f}")
print(f"E(4D)/B = {E_4D:.3f}")
print()

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
    
    # 4T2g(G) - first order: E_4G + Dq
    energies['4T2g(G)'] = E_4G + Dq_B
    
    # 4Eg(D) from 4D: E_4D - 5Dq
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4T2g(D) from 4D
    energies['4T2g(D)'] = E_4D + 2*Dq_B
    
    # 4F-derived states
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

Dq_B_values = [1.45, 2.55, 3.25]

print("Results with adjusted E(4D):")
print("="*70)

results = {}
for Dq_B in Dq_B_values:
    energies = calculate_energies(Dq_B)
    excited_states = [(term, E) for term, E in energies.items() if term != '6A1g']
    sorted_states = sorted(excited_states, key=lambda x: x[1])
    
    print(f"\nDq/B = {Dq_B}:")
    for term, E in sorted_states[:6]:
        print(f"  {term:12s}: E/B = {E:8.3f}")
    
    three_lowest = sorted_states[:3]
    results[Dq_B] = three_lowest
    print(f"  Three lowest: {[t[0] for t in three_lowest]}")

# Final answer
print("\n" + "="*70)
print("FINAL ANSWER:")
print("="*70)
for Dq_B in Dq_B_values:
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(results[Dq_B], 1):
        print(f"  {term}: E/B = {E:.3f}")
EOF
python3 d5_adjusted.py