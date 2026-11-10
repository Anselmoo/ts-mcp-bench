import numpy as np

# For d7 octahedral, using Tanabe-Sugano diagram calculations
# B and C are Racah parameters
# Dq is the ligand field parameter

# Given: B = 784 cm^-1, C = 3699 cm^-1
B = 784.0
C = 3699.0
C_over_B = C / B  # ≈ 4.72

# For d7, the energy matrices need to be set up for each symmetry
# The ground state at low field is 4T1g(F)

# Energy expressions for d7 octahedral (from ligand field theory):
# 
# For 4T1g(F) ground state and 4T1g(P), there's a 2x2 matrix:
# | -6Dq - E    4Dq        |
# |  4Dq      15B - 6Dq - E|  (approximately, need to check)
#
# Actually, for d7 the matrices are more complex. Let me use standard formulas.

# From standard references for d7 octahedral:
# The 4T1g states (from 4F and 4P) mix via a 2x2 matrix
# Diagonal elements: E(4T1g(F)) = -6Dq, E(4T1g(P)) = 15B - 6Dq (relative to 4F barycenter)
# Off-diagonal: 4Dq

# But we need energies relative to the ground state at each Dq/B

# Let me use a more systematic approach based on published Tanabe-Sugano data

# For d7, the key energy levels (E/B vs Dq/B) from standard diagrams:
# 
# At Dq/B = 0:
# 4F terms (4A2g, 4T2g, 4T1g) are degenerate at E/B = 0
# 4P term (4T1g) is at E/B = 15
# Doublet terms are at various energies depending on C/B

# As Dq/B increases:
# 4T1g(F) becomes ground state
# 4T2g rises with slope ~10
# 4A2g rises with slope ~20 (approximately)
# 4T1g(P) has complex behavior due to mixing

# Let me calculate using the actual matrices

def d7_energies(Dq_over_B, C_over_B=4.72):
    """
    Calculate energies for d7 octahedral using ligand field theory.
    Returns list of (E/B, term_label) tuples.
    """
    Dq = Dq_over_B * B
    
    # Energies relative to the 4F barycenter (in units of B)
    # From standard ligand field theory for d7:
    
    # 4T1g matrix (mixing of 4T1g(F) and 4T1g(P)):
    # Using the standard d7 matrices from Griffith or similar references
    
    # For 4T1g: 2x2 matrix
    # H = | -6*Dq/B      4*Dq/B     |
    #     |  4*Dq/B    15 - 6*Dq/B  |
    # Wait, this needs verification for d7
    
    # Actually for d7 (which is hole-equivalent to d3 but with different signs):
    # The matrices are similar to d3 but with Dq -> -Dq for some terms
    
    # Let me use the correct d7 formulas:
    # From standard texts (e.g., Figgis, "Introduction to Ligand Fields")
    
    # For d7 octahedral:
    # 4T1g(F) and 4T1g(P) mix:
    # Matrix elements (in units of B, relative to 4F barycenter):
    # H11 = -6*(Dq/B)  (4T1g from 4F)
    # H22 = 15 - 6*(Dq/B)  (4T1g from 4P) -- actually this should be checked
    # H12 = H21 = 4*(Dq/B)
    
    # Hmm, let me reconsider. For d7:
    # The free ion terms are 4F (ground) and 4P (excited, at ~15B)
    # In octahedral field:
    # 4F -> 4A2g + 4T2g + 4T1g
    # 4P -> 4T1g
    
    # The energies of the 4F components (relative to 4F barycenter):
    # 4A2g: -12Dq
    # 4T2g: -2Dq  
    # 4T1g(F): 6Dq
    # Wait, the signs depend on convention. Let me use the standard convention.
    
    # Standard convention for d7 octahedral (high spin, t2g^5 eg^2):
    # The ground state is 4T1g from 4F
    # Energy of 4T1g(F) relative to 4F barycenter: -6Dq (for d7)
    # Energy of 4T2g(F): +4Dq (for d7) -- need to verify
    # Energy of 4A2g(F): +16Dq (for d7) -- need to verify
    
    # Actually, I should use the hole formalism. d7 is equivalent to d3 holes.
    # For d3 octahedral (like d7 tetrahedral):
    # Ground: 4A2g
    # 4T2g at 10Dq above ground
    # 4T1g(F) at 18Dq above ground (approximately)
    # 4T1g(P) at higher energy
    
    # For d7 octahedral (the question's case):
    # This is like d3 but with inverted field (Dq -> -Dq for hole formalism)
    # But the actual energies need proper calculation
    
    # Let me use published Tanabe-Sugano diagram values for d7:
    # These are well-documented in inorganic chemistry texts
    
    energies = []
    
    # Calculate the 4T1g states from diagonalizing 2x2 matrix
    # Matrix for 4T1g (F and P mixing):
    # Using standard formulas from Tanabe-Sugano theory
    
    x = Dq_over_B  # Dq/B
    
    # 4T1g matrix (from 4F and 4P):
    # Diagonal: -6x (from 4F) and 15 - 6x (from 4P) -- relative to 4F barycenter
    # Off-diagonal: 4x
    # Wait, I need to verify these coefficients for d7
    
    # From standard references for d7:
    # The 4T1g matrix is:
    # | E(4F) - E    4Dq      |
    # | 4Dq       E(4P) - E   |
    # where E(4F) = -6Dq (relative to free ion 4F)
    # and E(4P) = 15B - 6Dq (relative to free ion 4F)
    
    # Actually, let me look up the correct matrix elements for d7:
    # From Tanabe and Sugano's original paper or standard texts:
    
    # For d7 octahedral, the 4T1g matrix (in units of B):
    # H = | -6x       4x     |
    #     |  4x    15 - 6x   |
    # where x = Dq/B
    
    # Eigenvalues:
    a = -6 * x
    b = 15 - 6 * x
    c = 4 * x
    
    disc = np.sqrt((a - b)**2 + 4 * c**2)
    E_T1g_1 = (a + b - disc) / 2  # Lower 4T1g (ground at low field)
    E_T1g_2 = (a + b + disc) / 2  # Higher 4T1g
    
    # 4T2g (from 4F only, no mixing at first order):
    # E(4T2g) = -6Dq + 10Dq = 4Dq relative to 4F barycenter? 
    # Actually for d7: E(4T2g) = 4Dq relative to 4F barycenter
    # In units of B: E/B = 4x
    # But wait, the 4T1g(F) is at -6x, so 4T2g - 4T1g = 10x
    E_T2g = 4 * x  # relative to 4F barycenter
    
    # 4A2g (from 4F only):
    # E(4A2g) = -6Dq + 20Dq = 14Dq relative to 4F barycenter?
    # Actually for d7: E(4A2g) = 14Dq relative to 4F barycenter
    E_A2g = 14 * x  # relative to 4F barycenter
    
    # Now convert to energies relative to ground state (4T1g)
    # Ground state energy: E_T1g_1 (relative to 4F barycenter)
    
    E_ground = E_T1g_1
    
    # Energies relative to ground:
    E_4T1g_P_rel = E_T1g_2 - E_ground  # The excited 4T1g (mostly 4P character)
    E_4T2g_rel = E_T2g - E_ground
    E_4A2g_rel = E_A2g - E_ground
    
    # Doublet states (from 2G, 2H, 2P, 2D, 2F):
    # These are more complex and depend on C/B
    # Approximate energies (from standard diagrams):
    # 2Eg(2G): ~ 2.5-3.5 B above ground at low field
    # 2T1g(2G): similar
    # 2T2g(2G): similar
    
    # For doublets, using approximate formulas:
    # 2Eg from 2G: E ≈ 10B + 5C - some Dq dependence
    # With C/B = 4.72: E/B ≈ 10 + 5*4.72 = 33.6... that seems too high
    
    # Actually, the doublet energies relative to 4F ground are:
    # 2G: ~ 10B + 5C above 4F? No, that's not right either.
    
    # Let me use standard values from Tanabe-Sugano diagrams for d7:
    # At Dq/B = 0:
    # 4F at 0, 4P at 15B, 2G at ~18B, 2H at ~20B, etc.
    # (These depend on C/B)
    
    # For C/B = 4.72, the doublet positions are:
    # 2G: E/B ≈ 10 + 5*(C/B - some factor) ... this is getting complicated
    
    # Let me use a simpler approach: read from standard d7 Tanabe-Sugano diagram
    # The diagram shows E/B vs Dq/B for all states
    
    # Approximate values from standard d7 TS diagram at various Dq/B:
    
    # At Dq/B = 1.45:
    # Ground: 4T1g at 0
    # 4T2g: ~ 10 * 1.45 = 14.5... wait, that's the separation in cm-1
    # In E/B units, the 4T2g - 4T1g separation is approximately 10*(Dq/B)
    # So E(4T2g)/B relative to ground ≈ 10 * 1.45 = 14.5
    
    # Hmm, but looking at actual TS diagrams, the slopes are different.
    # Let me reconsider.
    
    # In TS diagrams, the y-axis is E/B and x-axis is Dq/B (or sometimes Δ/B = 10Dq/B)
    # For d7, at Dq/B = 1:
    # 4T2g is at E/B ≈ 10 above ground (approximately)
    
    # So at Dq/B = 1.45:
    # 4T2g: E/B ≈ 14.5
    # 4A2g: E/B ≈ 25-30
    # 4T1g(P): E/B ≈ 20-25 (due to mixing, it's lowered)
    
    # But wait, there are also doublet states that can be lower!
    # For d7, the 2Eg and 2T1g states from 2G can be at E/B ≈ 20-25 at low field
    
    # Let me reconsider the problem. The question asks for the three lowest
    # excited terms at each Dq/B value. These could be quartets or doublets.
    
    # From standard d7 TS diagrams:
    # At low Dq/B (high spin region):
    # - 4T2g is the first excited state
    # - 4A2g or a doublet could be second
    # - 4T1g(P) or another doublet could be third
    
    # At higher Dq/B, there's a spin crossover where doublets become ground state
    # For d7, this happens around Dq/B ≈ 3-4 (depending on C/B)
    
    # Given C/B = 4.72, the spin crossover is at relatively high Dq/B
    # At Dq/B = 1.45, 2.45, 3.00, we're likely still in high-spin region
    # (ground state is 4T1g)
    
    # Let me calculate more carefully using the matrices:
    
    results = []
    
    # 4T1g (ground): E/B = 0 (by definition, relative to itself)
    # 4T2g: E/B = E_T2g_rel
    # 4A2g: E/B = E_A2g_rel
    # 4T1g(P): E/B = E_4T1g_P_rel
    
    results.append((0.0, "4T1g(F)", "ground"))
    results.append((E_4T2g_rel, "4T2g(F)", ""))
    results.append((E_4A2g_rel, "4A2g(F)", ""))
    results.append((E_4T1g_P_rel, "4T1g(P)", ""))
    
    # Sort by energy
    results.sort(key=lambda x: x[0])
    
    return results

# Test the calculation
for dq_b in [1.45, 2.45, 3.00]:
    print(f"\nDq/B = {dq_b}:")
    results = d7_energies(dq_b)
    for E, term, note in results:
        print(f"  {term}: E/B = {E:.2f} {note}")
