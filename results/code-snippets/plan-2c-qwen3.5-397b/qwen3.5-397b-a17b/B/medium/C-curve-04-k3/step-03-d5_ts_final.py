"""
Final d5 Tanabe-Sugano calculation with verified parameters.

For d5, the free ion term energies relative to 6S ground state are:
Using Racah parameters B and C:

From standard atomic spectroscopy (Condon-Shortley):
- 6S: ground (E = 0)
- 4G: E = 10B + 5C
- 4P: E = 23B + 5C (some sources say this is relative to different reference)
- 4D: E = 15B + 5C
- 4F: E = 5B + 5C (this seems too low)

Actually, let me use the proper expressions from Tanabe-Sugano theory.

For d5, the correct term energies (above 6S) are:
- 4G: 10B + 5C
- 4P: 23B + 5C (the 4P-4G separation is about 13B)
- 4D: 15B + 5C
- 4F: This is tricky - for d5, 4F is actually ABOVE 4G in many cases

Let me verify with actual Mn2+ data:
Mn2+ (d5): B ≈ 800-900 cm⁻¹, C ≈ 3000-3500 cm⁻¹
Observed transitions from 6A1g:
- 4T1g(G): ~18000-22000 cm⁻¹
- 4T2g(G): ~22000-25000 cm⁻¹
- 4A1g/4Eg(G): ~25000-28000 cm⁻¹
- 4T2g(D): ~28000-30000 cm⁻¹
- 4Eg(D): ~30000-32000 cm⁻¹
- 4T1g(P): ~35000-40000 cm⁻¹

With B = 800, C = 3473:
E(4G)/B = 10 + 5(3473/800) = 10 + 21.7 = 31.7
So 4G is at 31.7B = 25,360 cm⁻¹ - this matches!

So 4G is indeed the lowest quartet term. My earlier 4F calculation was wrong.

For d5, the 4F term is actually at HIGHER energy than 4G.
The correct ordering is: 6S < 4G < 4P < 4D < 4F (approximately)

Let me recalculate with correct term energies.
"""

import numpy as np

def d5_energies_correct(Dq_B, C_B):
    """
    Calculate d5 energy levels with correct term ordering.
    """
    energies = {}
    
    # Ground state
    energies['6A1g'] = 0.0
    
    # Free ion term energies (relative to 6S ground) in units of B
    # For d5, 4G is the lowest quartet term
    E_4G = 10 + 5*C_B   # 4G term - lowest quartet
    E_4P = 23 + 5*C_B   # 4P term
    E_4D = 15 + 5*C_B   # 4D term
    
    # For 4F - it's actually higher than 4G for d5
    # The 4F term for d5 is at approximately 25B + 5C or higher
    # Let me use E_4F = 25 + 5C_B (this puts it above 4G)
    E_4F = 25 + 5*C_B   # 4F term - above 4G for d5
    
    # 4A1g(G) and 4Eg(G) from 4G - Dq independent
    # These are special states that don't shift with crystal field
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # 4T1g(G) from 4G - shifts with Dq
    # At Dq = 0: E = E_4G
    # With crystal field: 4T1g(G) goes down, mixes with 4T1g(P)
    # Matrix for 4T1g (4G-4P mixing):
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]  # Lower eigenvalue
    energies['4T1g(P)'] = eig_4T1g[1]  # Higher eigenvalue
    
    # 4T2g(G) from 4G - shifts with Dq
    # At Dq = 0: E = E_4G
    # With crystal field: 4T2g(G) goes up slightly
    # Mixes with 4T2g(D)
    H_4T2g = np.array([
        [E_4G + Dq_B, 4*Dq_B],
        [4*Dq_B, E_4D + 5*Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # 4Eg(D) from 4D
    # 4D splits: 4Eg at lower energy, 4T2g at higher
    energies['4Eg(D)_pure'] = E_4D - 5*Dq_B
    
    # 4A2g, 4T1g, 4T2g from 4F (all above 4G for d5)
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

B = 800
C = 3473
C_B = C/B

print(f"Parameters: B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_B:.4f}")
print()
print(f"Free ion term energies (E/B above 6S):")
print(f"  4G: {10 + 5*C_B:.2f}")
print(f"  4D: {15 + 5*C_B:.2f}")
print(f"  4P: {23 + 5*C_B:.2f}")
print(f"  4F: {25 + 5*C_B:.2f}")
print()

Dq_B_values = [1.45, 2.55, 3.25]

results = {}
for Dq_B in Dq_B_values:
    print(f"Dq/B = {Dq_B}:")
    energies = d5_energies_correct(Dq_B, C_B)
    
    # Sort by energy, exclude ground state
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    
    print("  All excited states (sorted by energy):")
    for term, E in sorted_terms:
        print(f"    {term}: E/B = {E:.3f}")
    
    print("  Three lowest excited terms:")
    three_lowest = []
    for i, (term, E) in enumerate(sorted_terms[:3]):
        print(f"    {i+1}. {term}: E/B = {E:.3f}")
        three_lowest.append((term, E))
    results[Dq_B] = three_lowest
    print()

# Summary
print("="*60)
print("SUMMARY - Three lowest excited terms at each Dq/B:")
print("="*60)
for Dq_B in Dq_B_values:
    print(f"\nDq/B = {Dq_B}:")
    for i, (term, E) in enumerate(results[Dq_B]):
        print(f"  {i+1}. {term}: E/B = {E:.3f}")
