import numpy as np
import matplotlib.pyplot as plt

# Racah parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B  # = 4.794...

# For d4 configuration, we need to compute energies of all terms
# Free ion term energies relative to 5D barycenter (in units of B):
# 5D: 0 (reference)
# 3H: -3 + 2(C/B)
# 3P: 21 + 2(C/B)
# 3F: 5 + 3(C/B)
# 1G: 15 + 2(C/B)
# 1D: 17 + 2(C/B)
# 1S: 28 + 7(C/B)
# 1I: 1 + 7(C/B)

# Crystal field splitting patterns for octahedral symmetry:
# For each term, we need the Dq dependence

# 5D -> 5T2g (-6Dq), 5Eg (+4Dq)
# 3F -> 3A2g (-12Dq), 3T2g (-2Dq), 3T1g (+6Dq)
# 3P -> 3T1g (0 Dq dependence relative to term center)
# 3H -> 3A1g, 3Eg, 3T1g, 3T2g (complex splitting)

# For 3H (L=5), the splitting in Oh is:
# H -> A1 + E + T1 + T2
# The energies relative to 3H barycenter are:
# 3A1g: -10Dq (approximate, need proper calculation)
# Actually for d4, we need to use the strong field approach

# Let me use the known Tanabe-Sugano results for d4
# The key insight is that for d4, we have a hole-equivalent to d6

# Actually, let me compute this properly using the matrices

# For d^n configurations, we can use the strong-field basis
# t2g^4 eg^0, t2g^3 eg^1, t2g^2 eg^2, etc.

# But this is complex. Let me use known formulas.

# For d4 in octahedral field:
# Quintet states (from 5D):
# E(5T2g) = -6*Dq (relative to 5D center)
# E(5Eg) = +4*Dq (relative to 5D center)

# Triplet states from 3F:
# E(3A2g) = E(3F) - 12*Dq
# E(3T2g) = E(3F) - 2*Dq  
# E(3T1g from 3F) = E(3F) + 6*Dq

# Triplet state from 3P:
# E(3T1g from 3P) = E(3P) + 0*Dq (no first-order splitting)

# But 3T1g states mix! We need a 2x2 (or 3x3 including 3H) matrix

# For 3H term (L=5), splitting is more complex
# 3H -> 3A1g + 3Eg + 3T1g + 3T2g in Oh
# Energies relative to 3H center (from Griffith or similar):
# Using the formulas from standard references:

# Let me use a more systematic approach with known matrix elements

def compute_d4_energies(Dq_over_B, B_val, C_val):
    """Compute energy levels for d4 in octahedral field"""
    Dq = Dq_over_B * B_val
    
    # Free ion term energies relative to 5D (in cm^-1)
    E_5D = 0
    E_3H = (-3*B_val + 2*C_val)  # -3B + 2C
    E_3P = (21*B_val + 2*C_val)  # 21B + 2C
    E_3F = (5*B_val + 3*C_val)   # 5B + 3C
    E_1G = (15*B_val + 2*C_val)  # 15B + 2C
    E_1D = (17*B_val + 2*C_val)  # 17B + 2C
    E_1S = (28*B_val + 7*C_val)  # 28B + 7C
    E_1I = (1*B_val + 7*C_val)   # B + 7C
    
    levels = []
    
    # Quintet states (no mixing with other spin states)
    # 5T2g
    E_5T2g = E_5D - 6*Dq
    levels.append(('5T2g', E_5T2g))
    
    # 5Eg
    E_5Eg = E_5D + 4*Dq
    levels.append(('5Eg', E_5Eg))
    
    # Triplet states from 3F
    # 3A2g from 3F
    E_3A2g_3F = E_3F - 12*Dq
    levels.append(('3A2g(3F)', E_3A2g_3F))
    
    # 3T2g from 3F
    E_3T2g_3F = E_3F - 2*Dq
    levels.append(('3T2g(3F)', E_3T2g_3F))
    
    # 3T1g from 3F - will mix with 3T1g from 3P
    # For now, add the unmixed values, we'll handle mixing below
    
    # Triplet from 3P: 3T1g
    E_3T1g_3P = E_3P  # No first-order Dq dependence
    
    # 3T1g mixing matrix (3F and 3P contributions)
    # The off-diagonal matrix element is 4*sqrt(3)*Dq (from standard tables)
    # Actually for d4, the mixing is more complex
    
    # Let me use the proper 2x2 matrix for 3T1g states
    # From Tanabe-Sugano theory for d4:
    # The 3T1g states from 3F and 3P mix
    # Matrix: [[E_3F + 6Dq, 4*sqrt(3)*Dq], [4*sqrt(3)*Dq, E_3P]]
    
    H_3T1g = np.array([
        [E_3F + 6*Dq, 4*np.sqrt(3)*Dq],
        [4*np.sqrt(3)*Dq, E_3P]
    ])
    eig_3T1g = np.linalg.eigvalsh(H_3T1g)
    levels.append(('3T1g(lower)', eig_3T1g[0]))
    levels.append(('3T1g(upper)', eig_3T1g[1]))
    
    # 3H term splitting (L=5 -> A1 + E + T1 + T2 in Oh)
    # Using formulas from standard references for d4
    # The 3H term splits into: 3A1g, 3Eg, 3T1g, 3T2g
    # With Dq dependence (relative to 3H center):
    # These require a more complex treatment
    
    # For 3H, using the strong-field approach:
    # 3A1g: -15Dq (approximate)
    # 3Eg: -5Dq (approximate)
    # 3T1g: +5Dq (approximate) - will mix with other 3T1g
    # 3T2g: +10Dq (approximate)
    
    # Actually, let me use proper values from literature
    # For d4, the 3H splitting in octahedral field:
    # Using the formulas from "The Theory of Transition Metal Ions" by Griffith
    
    # 3A1g from 3H
    E_3A1g_3H = E_3H - 15*Dq
    levels.append(('3A1g(3H)', E_3A1g_3H))
    
    # 3Eg from 3H
    E_3Eg_3H = E_3H - 5*Dq
    levels.append(('3Eg(3H)', E_3Eg_3H))
    
    # 3T2g from 3H - this will mix with 3T2g from 3F
    E_3T2g_3H = E_3H + 10*Dq
    
    # Mix 3T2g states from 3F and 3H
    # Off-diagonal element is approximately 2*sqrt(6)*Dq
    H_3T2g = np.array([
        [E_3T2g_3F, 2*np.sqrt(6)*Dq],
        [2*np.sqrt(6)*Dq, E_3T2g_3H]
    ])
    eig_3T2g = np.linalg.eigvalsh(H_3T2g)
    levels.append(('3T2g(lower)', eig_3T2g[0]))
    levels.append(('3T2g(upper)', eig_3T2g[1]))
    
    # 3T1g from 3H - this will mix with the other 3T1g states
    E_3T1g_3H = E_3H + 5*Dq
    
    # Now we have a 3x3 matrix for 3T1g (from 3F, 3P, and 3H)
    # This is getting complex. Let me simplify.
    
    # Singlet states
    # 1A1g from 1S
    E_1A1g_1S = E_1S
    levels.append(('1A1g(1S)', E_1A1g_1S))
    
    # 1A1g from 1G
    E_1A1g_1G = E_1G
    levels.append(('1A1g(1G)', E_1A1g_1G))
    
    # 1Eg from 1G
    E_1Eg_1G = E_1G
    levels.append(('1Eg(1G)', E_1Eg_1G))
    
    # 1Eg from 1D
    E_1Eg_1D = E_1D
    levels.append(('1Eg(1D)', E_1Eg_1D))
    
    # 1T1g from 1G
    E_1T1g_1G = E_1G
    levels.append(('1T1g(1G)', E_1T1g_1G))
    
    # 1T2g from 1G
    E_1T2g_1G = E_1G
    levels.append(('1T2g(1G)', E_1T2g_1G))
    
    # 1T2g from 1D
    E_1T2g_1D = E_1D
    levels.append(('1T2g(1D)', E_1T2g_1D))
    
    # 1I term splits into 1A1g, 1Eg, 1T1g, 1T2g
    E_1A1g_1I = E_1I
    levels.append(('1A1g(1I)', E_1A1g_1I))
    
    E_1Eg_1I = E_1I
    levels.append(('1Eg(1I)', E_1Eg_1I))
    
    E_1T1g_1I = E_1I
    levels.append(('1T1g(1I)', E_1T1g_1I))
    
    E_1T2g_1I = E_1I
    levels.append(('1T2g(1I)', E_1T2g_1I))
    
    return levels

# This approach is too simplified. Let me use a proper implementation
# based on the actual Tanabe-Sugano matrices for d4

print("Computing d4 Tanabe-Sugano diagram...")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C/B:.4f}")
