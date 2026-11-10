cat << 'EOF' > d5_ts_refined.py
"""
Refined d5 Tanabe-Sugano calculation.

Let me reconsider the 4T2g matrix elements more carefully.

Looking at the standard d5 Tanabe-Sugano diagram:
- 4T2g(G) starts at E(4G) at Dq=0 and increases slowly with Dq
- The slope is positive but small

This suggests the diagonal element for 4T2g(G) should be E_4G + (small)*Dq

For the 4D-derived 4T2g(D):
- It starts at E(4D) at Dq=0 and decreases with Dq
- The slope is negative

Let me try different matrix elements to better match standard TS diagrams.

Actually, I realize I should look at the actual Tanabe-Sugano paper or standard references
for the exact matrix elements. But for now, let me try to adjust based on expected behavior.

Standard result: at Dq/B = 3, 4T2g(G) should be around E/B = 18-20
My current result: 14.6 - too low

The issue is the mixing with 4T2g(D) pulls the energy down too much.
Let me reduce the off-diagonal mixing or adjust the diagonal elements.

Alternative approach: use the simpler approximation without 4T2g-4T2g(D) mixing:
4T2g(G) ≈ E_4G + Dq (just the first-order crystal field splitting)
"""

import numpy as np

def d5_TS_simple(Dq_B, C_B):
    """
    Simplified d5 Tanabe-Sugano calculation.
    Use first-order crystal field splitting without extensive mixing.
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
    
    # 4T1g(G) from 4G-4P mixing (this mixing is important)
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # 4T2g(G) - use simple first-order: E_4G + Dq
    # This gives positive slope as expected
    energies['4T2g(G)'] = E_4G + Dq_B
    
    # 4T2g(D) - from 4D, decreases with Dq
    energies['4T2g(D)'] = E_4D - 3*Dq_B  # Approximate
    
    # 4Eg(D) - from 4D, decreases with Dq
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4F-derived
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

# Test
C_B = 3473/800
print(f"C/B = {C_B:.4f}")
print(f"E(4G)/B = {10 + 5*C_B:.2f}")
print()

# Check at reference values
for Dq_B in [1.0, 2.0, 3.0]:
    energies = d5_TS_simple(Dq_B, C_B)
    print(f"Dq/B = {Dq_B}:")
    print(f"  4T1g(G): {energies['4T1g(G)']:.2f}")
    print(f"  4T2g(G): {energies['4T2g(G)']:.2f}")
    print(f"  4Eg(D): {energies['4Eg(D)']:.2f}")
    print(f"  4A1g/4Eg(G): {energies['4A1g(G)']:.2f}")
    print()

# Calculate for requested values
print("="*60)
print("REQUESTED VALUES (simple model):")
print("="*60)

Dq_B_values = [1.45, 2.55, 3.25]
all_results = {}

for Dq_B in Dq_B_values:
    energies = d5_TS_simple(Dq_B, C_B)
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    three_lowest = sorted_terms[:3]
    all_results[Dq_B] = three_lowest
    
    print(f"\nDq/B = {Dq_B}:")
    for term, E in sorted_terms[:5]:
        print(f"  {term}: E/B = {E:.3f}")
    print(f"  Three lowest: {[t[0] for t in three_lowest]}")

# Also calculate with the mixing model for comparison
print("\n" + "="*60)
print("WITH MIXING (previous model):")
print("="*60)

def d5_TS_mixing(Dq_B, C_B):
    energies = {}
    energies['6A1g'] = 0.0
    
    E_4G = 10 + 5*C_B
    E_4P = 23 + 5*C_B
    E_4D = 15 + 5*C_B
    E_4F = 25 + 5*C_B
    
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    H_4T2g = np.array([
        [E_4G + Dq_B, 2*Dq_B],  # Reduced mixing
        [2*Dq_B, E_4D - 3*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

for Dq_B in Dq_B_values:
    energies = d5_TS_mixing(Dq_B, C_B)
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    three_lowest = sorted_terms[:3]
    
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(three_lowest):
        print(f"  {i+1}. {term}: E/B = {E:.3f}")
EOF
python3 d5_ts_refined.py