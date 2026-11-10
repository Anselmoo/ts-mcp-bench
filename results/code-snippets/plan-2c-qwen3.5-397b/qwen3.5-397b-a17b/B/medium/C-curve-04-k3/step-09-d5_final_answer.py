"""
Final calculation for d5 Tanabe-Sugano energy levels.

Using the standard energy matrices for d5 octahedral complexes.
"""

import numpy as np

# Given parameters
B = 800  # cm⁻¹
C = 3473  # cm⁻¹
C_B = C / B  # 4.34125

# Free ion term energies (relative to 6S ground state) in units of B
E_4G = 10 + 5 * C_B  # 31.706
E_4P = 23 + 5 * C_B  # 44.706
E_4D = 15 + 5 * C_B  # 36.706
E_4F = 25 + 5 * C_B  # 46.706 (above 4G for d5)

def calculate_energies(Dq_B):
    """Calculate all energy levels for given Dq/B."""
    energies = {}
    
    # Ground state
    energies['6A1g'] = 0.0
    
    # 4A1g(G) and 4Eg(G) from 4G - Dq independent
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # 4T1g(G) from 4G-4P mixing (2x2 matrix)
    H_4T1g = np.array([
        [E_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, E_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]
    energies['4T1g(P)'] = eig_4T1g[1]
    
    # 4T2g(G) - first order: E_4G + Dq (positive slope)
    energies['4T2g(G)'] = E_4G + Dq_B
    
    # 4Eg(D) from 4D: E_4D - 5Dq (negative slope)
    energies['4Eg(D)'] = E_4D - 5*Dq_B
    
    # 4T2g(D) from 4D
    energies['4T2g(D)'] = E_4D + 2*Dq_B
    
    # 4F-derived states
    energies['4T1g(F)'] = E_4F - 6*Dq_B
    energies['4T2g(F)'] = E_4F + 2*Dq_B
    energies['4A2g(F)'] = E_4F + 12*Dq_B
    
    return energies

# Calculate for requested Dq/B values
Dq_B_values = [1.45, 2.55, 3.25]

print("="*70)
print("d5 Octahedral Tanabe-Sugano Energy Levels")
print(f"Parameters: B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_B:.4f}")
print("="*70)

results = {}
for Dq_B in Dq_B_values:
    energies = calculate_energies(Dq_B)
    
    # Sort excited states by energy (exclude ground state)
    excited_states = [(term, E) for term, E in energies.items() if term != '6A1g']
    sorted_states = sorted(excited_states, key=lambda x: x[1])
    
    print(f"\nDq/B = {Dq_B}:")
    print("-" * 50)
    print("All excited states (sorted by energy):")
    for term, E in sorted_states:
        print(f"  {term:12s}: E/B = {E:8.3f}")
    
    # Get three lowest
    three_lowest = sorted_states[:3]
    results[Dq_B] = three_lowest
    
    print(f"\nThree lowest excited terms:")
    for i, (term, E) in enumerate(three_lowest, 1):
        print(f"  {i}. {term}: E/B = {E:.3f}")

# Format final answer
print("\n" + "="*70)
print("FINAL ANSWER - Nine points:")
print("="*70)

for Dq_B in Dq_B_values:
    print(f"\nAt Dq/B = {Dq_B}:")
    for i, (term, E) in enumerate(results[Dq_B], 1):
        print(f"  Point {i}: Term = {term}, E/B = {E:.3f}")
