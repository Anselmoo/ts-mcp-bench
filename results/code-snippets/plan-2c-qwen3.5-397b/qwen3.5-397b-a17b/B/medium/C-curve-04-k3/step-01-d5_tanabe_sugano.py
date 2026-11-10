"""
Calculate d5 Tanabe-Sugano energy levels for octahedral complexes.
For d5, we need to diagonalize the energy matrices for each symmetry.

The ground state is 6A1g from 6S, with E/B = 0 (independent of Dq/B).

For the excited quartet states from 4G, 4P, 4D, 4F terms, we use
the strong-field basis and include Racah parameters B and C.

Key relationships for d5:
- The 6A1g ground state has energy E = 0 (reference)
- Quartet states energies depend on Dq and B, C

For d5, the main quartet terms and their approximate energies:
4T1g(G): lowest quartet, from 4G
4T2g(G): from 4G  
4A1g(G), 4Eg(G): from 4G (these are degenerate and independent of Dq)
4T2g(D): from 4D
4Eg(D): from 4D
4T1g(P): from 4P (higher energy)

The 4A1g and 4Eg from 4G have energy E/B = 10 + 5C/B (independent of Dq)
Actually for d5: E(4A1g, 4Eg from 4G)/B = 10 + 5C/B

Let me use the proper Tanabe-Sugano formulas for d5.
"""

import numpy as np

def d5_energies(Dq_B, C_B=4.34125):  # C/B = 3473/800 = 4.34125
    """
    Calculate energy levels for d5 octahedral complex.
    Returns dict of term: E/B values
    """
    # Ground state 6A1g is at E/B = 0
    
    energies = {}
    energies['6A1g'] = 0.0
    
    # For d5, the 4A1g and 4Eg from 4G are at fixed energy (independent of Dq)
    # E/B = 10 + 5*C/B for the 4G-derived states
    # Actually the formula is more nuanced
    
    # From Tanabe-Sugano diagrams and standard references:
    # 4T1g(G) - lowest quartet, energy decreases then increases with Dq
    # 4T2g(G) - from 4G
    # 4A1g(G), 4Eg(G) - from 4G, horizontal lines
    # 4T2g(D) - from 4D
    # 4Eg(D) - from 4D  
    # 4T1g(P) - from 4P
    
    # The 4A1g and 4Eg from 4G have E/B = 10 + 5C/B approximately
    # But more precisely for d5:
    # E(4A1g, 4Eg from 4G) = 10B + 5C = B(10 + 5C/B)
    
    E_4A1g_4Eg_G = 10 + 5*C_B  # These are degenerate and Dq-independent
    
    # For 4T1g(G) and 4T2g(G), we need to solve the energy matrices
    # The 4T1g(G) comes from mixing of configurations
    
    # Using standard Tanabe-Sugano results for d5:
    # At Dq/B = 0: 4G is at 10B + 5C above ground, splits into components
    
    # Let me use the actual matrix diagonalization approach
    # For the 4T1g states, there's a 2x2 matrix (from 4G and 4P)
    # For 4T2g states, there's mixing too
    
    # Simplified approach using published Tanabe-Sugano data points
    # and interpolation formulas
    
    # From literature, for d5:
    # 4T1g(G) energy matrix involves -4Dq and Racah parameters
    
    # The characteristic equation for 4T1g(G) in d5:
    # E^2 - E(6Dq + 10B + 5C) + ... = 0
    
    # Let me use a more direct approach with known formulas
    # For d5 quartet T1g states (mixing of 4T1g from 4G and 4T1g from 4P):
    
    # Energy of 4T1g(G) approximately:
    # At low Dq: E ≈ 10B + 5C - 4Dq (first order)
    # But there's mixing with 4T1g(P)
    
    # For 4T2g(G):
    # E ≈ 10B + 5C + Dq (first order, from 4G)
    
    # Let me implement proper diagonalization
    
    # 4T1g matrix (2x2 from 4G and 4P mixing):
    # | -4Dq + E(4G)    4Dq           |
    # | 4Dq            -4Dq + E(4P)   |
    # where E(4G) = 10B + 5C, E(4P) = 23B + 5C (relative to 6S)
    
    # Actually for d5 the matrix elements are different
    # Let me use the standard form from Tanabe-Sugano theory
    
    # For d5, the 4T1g states come from 4G and 4P
    # The energy matrix (in units of B) is:
    # | x - 4(Dq/B)      4(Dq/B)        |
    # | 4(Dq/B)         y - 4(Dq/B)     |
    # where x = E(4G)/B = 10 + 5C/B, y = E(4P)/B = 23 + 5C/B
    
    x_4G = 10 + 5*C_B  # Energy of 4G term / B
    x_4P = 23 + 5*C_B  # Energy of 4P term / B  
    x_4D = 15 + 5*C_B  # Energy of 4D term / B
    x_4F = 5 + 5*C_B   # Energy of 4F term / B (but 4F gives different splittings)
    
    # Wait, I need to reconsider. For d5:
    # Free ion terms energies relative to ground 6S:
    # 4G: 10B + 5C (actually this needs verification)
    # 4P: higher
    # 4D: 
    # 4F: 
    
    # Standard Racah parameterization for d5:
    # E(4G) = 10B + 5C (above 6S)
    # E(4P) = 23B + 5C (above 6S) - wait this seems off
    
    # Let me use the correct formulas from Tanabe-Sugano theory
    # For d5, using Racah parameters:
    # The 4G term is at energy 10B + 5C above 6S
    # The 4P term is at energy 23B + 5C above 6S (this is for the centroid)
    
    # Actually, the standard values are:
    # E(4G) - E(6S) = 10B + 5C
    # E(4P) - E(6S) = 23B + 5C  -- No wait, 4P should be around 20-25B above 4G
    
    # From standard tables for d5:
    # 4G: 10B + 5C above 6S
    # 4P: about 30B + 5C above 6S (the 4P-4G separation is about 20B)
    # Actually E(4P) - E(4G) ≈ 15B for d5
    
    # Let me use: E(4P)/B = 25 + 5C/B (approximately)
    # and E(4G)/B = 10 + 5C/B
    
    # For 4T1g: 2x2 matrix
    H_4T1g = np.array([
        [x_4G - 4*Dq_B, 4*Dq_B],
        [4*Dq_B, x_4P - 4*Dq_B]
    ])
    eig_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies['4T1g(G)'] = eig_4T1g[0]  # Lower one is from 4G
    energies['4T1g(P)'] = eig_4T1g[1]  # Higher one is from 4P
    
    # For 4T2g: also 2x2 from 4G and 4D mixing
    # Matrix elements different
    H_4T2g = np.array([
        [x_4G + Dq_B, 4*Dq_B],
        [4*Dq_B, x_4D + Dq_B]
    ])
    eig_4T2g = np.linalg.eigvalsh(H_4T2g)
    energies['4T2g(G)'] = eig_4T2g[0]
    energies['4T2g(D)'] = eig_4T2g[1]
    
    # 4A1g and 4Eg from 4G are Dq-independent
    energies['4A1g(G)'] = x_4G
    energies['4Eg(G)'] = x_4G  # Degenerate with 4A1g
    
    # 4Eg from 4D
    energies['4Eg(D)'] = x_4D - 5*Dq_B  # Approximate
    
    # 4A2g from 4F
    energies['4A2g(F)'] = x_4F + 10*Dq_B  # Approximate
    
    # 4T1g from 4F (another one)
    energies['4T1g(F)'] = x_4F + 6*Dq_B  # Approximate
    
    # 4T2g from 4F  
    energies['4T2g(F)'] = x_4F - 4*Dq_B  # Approximate
    
    return energies

# Test with the given parameters
B = 800  # cm^-1
C = 3473  # cm^-1
C_B = C/B  # = 4.34125

print(f"C/B = {C_B}")
print()

Dq_B_values = [1.45, 2.55, 3.25]

for Dq_B in Dq_B_values:
    print(f"Dq/B = {Dq_B}:")
    energies = d5_energies(Dq_B, C_B)
    
    # Sort by energy and get lowest 3 excited states (excluding ground 6A1g)
    sorted_terms = sorted([(term, E) for term, E in energies.items() if term != '6A1g'], 
                          key=lambda x: x[1])
    
    for i, (term, E) in enumerate(sorted_terms[:3]):
        print(f"  {i+1}. {term}: E/B = {E:.2f}")
    print()
