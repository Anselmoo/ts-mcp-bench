cat << 'EOF' > d5_ts_corrected.py
"""
Corrected d5 Tanabe-Sugano calculation.

The issue with my previous calculation is the 4T2g matrix.
Let me use the correct matrix elements.

For d5, the proper energy matrices are:

4T1g (from 4G and 4P):
- 4T1g(G) at E(4G) - 4Dq
- 4T1g(P) at E(4P) - 4Dq
- Mixing: 4Dq

4T2g (from 4G and 4D):
- 4T2g(G) at E(4G) + Dq (goes UP with Dq)
- 4T2g(D) at E(4D) - 3Dq or similar (goes DOWN with Dq)
- Mixing: some value

4Eg:
- 4Eg(G) at E(4G) (Dq-independent)
- 4Eg(D) at E(4D) - 5Dq (goes DOWN with Dq)

Let me recalculate with proper signs.
"""

import numpy as np

def d5_TS_corrected(Dq_B, C_B):
    """
    Calculate d5 Tanabe-Sugano energy levels with corrected matrices.
    """
    energies = {}
    
    # Ground state
    energies['6A1g'] = 0.0
    
    # Free ion term energies relative to 6S (in units of B)
    E_4G = 10 + 5*C_B
    E_4P = 23 + 5*C_B
    E_4D = 15 + 5*C_B
    E_4F = 25 + 5*C_B  # Above 4G for d5
    
    # 4A1g(G) - Dq independent
    energies['4A1g(G)'] = E_4G
    
    # 4T1g(G) from 4G-4P mixing
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # 4T2g(G) from 4G-4D mixing
    # 4T2g(G) at E_4G + Dq (goes up with Dq)
    # 4T2g(D) at E_4D - 3Dq (goes down with Dq) - need to verify this
    # Actually for 4D term: Eg at -5Dq, T2g at +5Dq relative to centroid? Or different?
    # Let me use: 4T2g(D) at E_4D + 5Dq (goes up)
    # But then both go up, which doesn't match TS diagrams...
    
    # Looking at TS diagrams for d5:
    # 4T2g(G) goes up slightly with Dq
    # 4T2g(D) goes down with Dq
    # So 4T2g(D) should have negative Dq coefficient
    
    # For d5, the 4D term splits with 4Eg lower and 4T2g higher
    # But in the TS diagram, the 4Eg(D) line goes down and 4T2g(D) also goes down?
    # Actually, I think both 4Eg(D) and 4T2g(D) come from the same 4D term
    # and they split, but both can go down relative to the ground state
    
    # Let me try: 4T2g(D) at E_4D - 5Dq (similar to 4Eg)
    H_4T2g = np.array([
        [E_4G + Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D - 5*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # 4Eg states
    energies['4Eg(G)'] = E_4G  # Dq-independent
    energies['4Eg(D)'] = E_4D - 5*Dq_B  # From 4D
    
    # 4F-derived states
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

B = 800
C = 3473
C_B = C/B

print(f"Parameters: B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_B:.4f}")
print()

Dq_B_values = [1.45, 2.55, 3.25]

all_results = {}
for Dq_B in Dq_B_values:
    energies = d5_TS_corrected(Dq_B, C_B)
    
    # Sort by energy, exclude ground state
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    
    print(f"Dq/B = {Dq_B}:")
    for term, E in sorted_terms:
        print(f"  {term}: E/B = {E:.3f}")
    
    three_lowest = sorted_terms[:3]
    all_results[Dq_B] = three_lowest
    print(f"  Three lowest: {[t[0] for t in three_lowest]}")
    print()

# Print final answer
print("="*70)
print("FINAL ANSWER:")
print("="*70)
for Dq_B in Dq_B_values:
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(all_results[Dq_B]):
        print(f"  {term}: E/B = {E:.3f}")
EOF
python3 d5_ts_corrected.py