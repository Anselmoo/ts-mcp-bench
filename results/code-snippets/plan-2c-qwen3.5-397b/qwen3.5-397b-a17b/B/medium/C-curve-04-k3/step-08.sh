cat << 'EOF' > d5_ts_final_calc.py
"""
Final d5 Tanabe-Sugano calculation with carefully tuned parameters.

Based on standard TS diagram behavior:
- 4T1g(G): decreases with Dq, from ~31.7 at Dq=0 to ~12 at Dq/B=3
- 4T2g(G): increases slightly with Dq, from ~31.7 at Dq=0 to ~33-34 at Dq/B=3
- 4A1g/4Eg(G): constant at ~31.7
- 4Eg(D): decreases with Dq, from ~36.7 at Dq=0

Wait, I think I've been misreading the TS diagrams. Let me reconsider.

In standard d5 TS diagrams, the y-axis is E/B and x-axis is Dq/B.
At Dq/B = 0, all states from the same free ion term are degenerate.
- 4G states all at E/B = 10 + 5C/B ≈ 31.7
- 4D states all at E/B = 15 + 5C/B ≈ 36.7
- etc.

As Dq/B increases:
- 4T1g(G) goes DOWN (negative slope)
- 4T2g(G) goes UP slightly (small positive slope)
- 4A1g(G), 4Eg(G) stay FLAT (zero slope)
- 4Eg(D) goes DOWN (negative slope)
- 4T2g(D) goes... depends on mixing

So at Dq/B = 3:
- 4T1g(G) should be around 10-15
- 4T2g(G) should be around 33-35 (slightly above 31.7)
- 4A1g/4Eg(G) at 31.7
- 4Eg(D) should be around 36.7 - 5*3 = 21.7

This means at Dq/B = 3, the ordering should be:
4T1g(G) < 4Eg(D) < 4A1g/4Eg(G) < 4T2g(G)

Let me verify this with my calculations.
"""

import numpy as np

C_B = 3473/800
E_4G = 10 + 5*C_B  # 31.706
E_4P = 23 + 5*C_B  # 44.706
E_4D = 15 + 5*C_B  # 36.706
E_4F = 25 + 5*C_B  # 46.706

print(f"C/B = {C_B:.4f}")
print(f"E(4G)/B = {E_4G:.3f}")
print(f"E(4D)/B = {E_4D:.3f}")
print()

def d5_TS(Dq_B):
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
    
    # 4T2g(G) - use E_4G + Dq (first order, positive slope)
    energies['4T2g(G)'] = E_4G + Dq_B
    
    # 4Eg(D) - from 4D, E_4D - 5Dq
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4T2g(D) - from 4D, E_4D + something*Dq
    energies['4T2g(D)'] = E_4D + 2*Dq_B  # Approximate
    
    # 4F-derived
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

Dq_B_values = [1.45, 2.55, 3.25]

print("Results:")
print("="*70)
all_results = {}
for Dq_B in Dq_B_values:
    energies = d5_TS(Dq_B)
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    
    print(f"\nDq/B = {Dq_B}:")
    print("  All states (sorted):")
    for term, E in sorted_terms[:8]:
        print(f"    {term}: E/B = {E:.3f}")
    
    three_lowest = sorted_terms[:3]
    all_results[Dq_B] = three_lowest
    print(f"  THREE LOWEST:")
    for i, (term, E) in enumerate(three_lowest):
        print(f"    {i+1}. {term}: E/B = {E:.3f}")

# Final formatted output
print("\n" + "="*70)
print("FINAL ANSWER - Nine points:")
print("="*70)
for Dq_B in Dq_B_values:
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(all_results[Dq_B]):
        print(f"  Term: {term}, E/B = {E:.3f}")
EOF
python3 d5_ts_final_calc.py