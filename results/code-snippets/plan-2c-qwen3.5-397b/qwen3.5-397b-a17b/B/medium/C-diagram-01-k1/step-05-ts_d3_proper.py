import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Parameters for d3 ion
B = 828  # cm^-1
C = 3390  # cm^-1
C_over_B = C / B  # = 4.094202898550725

# Dq/B values to compute
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

def d3_energies(dq_over_b, C_over_B=4.094202898550725):
    """
    Compute energy levels for d3 octahedral complex using proper Tanabe-Sugano formalism.
    
    For d3, the ground state is always 4A2g. The key is to use the correct
    free-ion term energies and crystal field matrices.
    
    Free ion term energies (relative to 4F ground term, in units of B):
    - 4P: 15
    - 2G: 9 + 3*C/B (from Racah: E(2G) - E(4F) = 6B + 3C for d3)
    - 2H: 9 + 3*C/B
    - 2P: 18 + 3*C/B
    
    Wait, let me recalculate using proper Racah formulas for d3:
    E(4F) = 3A - 15B
    E(4P) = 3A
    E(2G) = E(2H) = 3A - 9B + 3C
    E(2P) = 3A + 3B + 3C
    
    Relative to 4F:
    E(4P) - E(4F) = 15B
    E(2G) - E(4F) = 6B + 3C
    E(2P) - E(4F) = 18B + 3C
    
    With C/B = 4.094:
    E(2G)/B relative to 4F = 6 + 3*4.094 = 18.28
    """
    x = dq_over_b  # Dq/B
    
    levels = []
    
    # === QUARTET STATES ===
    # 4A2g is ground state, set to E/B = 0
    levels.append((0.0, '4A2g'))
    
    # 4T2g: at 10Dq above 4A2g
    levels.append((10 * x, '4T2g'))
    
    # 4T1g: mixing between 4T1g(F) and 4T1g(P)
    # Matrix relative to 4A2g:
    # 4T1g(F) at 18Dq above 4A2g
    # 4T1g(P) at 15B + 18Dq above 4A2g
    # Off-diagonal: 4Dq
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))
    levels.append((eig_4t1g[1], '4T1g'))
    
    # === DOUBLE STATES ===
    # Free ion energies relative to 4F (in units of B):
    E_2G_4F = 6 + 3*C_over_B   # = 18.28
    E_2H_4F = 6 + 3*C_over_B   # = 18.28
    E_2P_4F = 18 + 3*C_over_B  # = 30.28
    
    # Now, the key insight: these energies are relative to 4F TERM,
    # but 4A2g is at -12Dq relative to 4F TERM (in the crystal field).
    # So relative to 4A2g, we need to add 12Dq = 12x*B.
    
    # Actually no - in the Tanabe-Sugano convention, we set 4A2g to 0 at all Dq.
    # The free-ion term energies are fixed (don't depend on Dq).
    # The crystal field splitting is applied relative to each term's barycenter.
    
    # For 4F term:
    # - 4A2g at -12Dq relative to 4F barycenter
    # - 4T2g at -2Dq relative to 4F barycenter
    # - 4T1g at +6Dq relative to 4F barycenter
    # Setting 4A2g to 0: add 12Dq to all
    # - 4A2g: 0
    # - 4T2g: 10Dq
    # - 4T1g: 18Dq
    
    # For 2G term (at 6B + 3C above 4F):
    # - 2Eg at +2Dq relative to 2G barycenter
    # - 2T1g at -Dq relative to 2G barycenter
    # - 2T2g at +Dq relative to 2G barycenter
    # Relative to 4A2g: (6B + 3C) + crystal_field_shift + 12Dq
    # Wait, that's not right either.
    
    # Let me think again. The 2G term energy is 6B + 3C above the 4F TERM.
    # At Dq=0, 4A2g is at the 4F term energy, so 2G is at 6B + 3C above 4A2g.
    # At Dq>0, 4A2g is still defined as 0 (Tanabe-Sugano convention).
    # The 2G term barycenter is still at 6B + 3C above the 4F term.
    # But the 4F term components have split, with 4A2g being the lowest.
    
    # The key is: the 2G term energy (6B + 3C above 4F) is a FREE ION property.
    # It doesn't change with Dq. What changes is how 2G splits in the crystal field.
    
    # So relative to 4A2g (which is at 0 by convention):
    # 2G barycenter is at 6B + 3C + (energy of 4F term - energy of 4A2g)
    # At Dq=0: 4F term = 4A2g, so 2G is at 6B + 3C above 4A2g.
    # At Dq>0: 4A2g is at -12Dq relative to 4F barycenter.
    #         4F term is at -6B relative to 4F barycenter.
    #         So 4A2g is at (-6B - 12Dq) - (-6B) = -12Dq relative to 4F term.
    #         Wait, that's circular.
    
    # Let me use a different approach. In Tanabe-Sugano diagrams:
    # - The ground state (4A2g for d3) is always at E = 0.
    # - All other energies are measured relative to this.
    # - At Dq=0, the free-ion terms are at their Racah energies.
    # - As Dq increases, crystal field splitting is applied.
    
    # For d3 at Dq=0:
    # - 4F (including 4A2g, 4T2g, 4T1g): E = 0
    # - 4P (4T1g): E = 15B
    # - 2G, 2H: E = 6B + 3C
    # - 2P: E = 18B + 3C
    
    # For d3 at Dq>0:
    # - 4A2g: E = 0 (by convention)
    # - 4T2g: E = 10Dq (relative to 4A2g)
    # - 4T1g: from diagonalizing 2x2 matrix
    # - 2G components: E = (6B + 3C) + crystal_field_splitting
    # - etc.
    
    # The crystal field splitting within 2G:
    # - 2Eg: +2Dq relative to 2G barycenter
    # - 2T1g: -Dq relative to 2G barycenter
    # - 2T2g: +Dq relative to 2G barycenter
    
    # So relative to 4A2g:
    # - 2Eg(G): (6B + 3C) + 2Dq = 6 + 3*C/B + 2x (in units of B)
    # - 2T1g(G): (6B + 3C) - Dq = 6 + 3*C/B - x
    # - 2T2g(G): (6B + 3C) + Dq = 6 + 3*C/B + x
    
    # For 2H (same barycenter as 2G):
    # The crystal field splitting is different:
    # - 2Eg(H): -3Dq relative to 2H barycenter (from group theory)
    # - 2T1g(H): +Dq relative to 2H barycenter
    # - 2T2g(H): +2Dq relative to 2H barycenter
    
    # So:
    # - 2Eg(H): (6B + 3C) - 3Dq = 6 + 3*C/B - 3x
    # - 2T1g(H): (6B + 3C) + Dq = 6 + 3*C/B + x
    # - 2T2g(H): (6B + 3C) + 2Dq = 6 + 3*C/B + 2x
    
    # Now, 2G and 2H are degenerate free-ion terms, so they mix.
    # We need to diagonalize 2x2 matrices for each symmetry.
    
    # For 2Eg:
    # H = | E_2G + 2x    V    |
    #     | V         E_2H - 3x|
    # where E_2G = E_2H = 6 + 3*C/B
    # and V is the mixing matrix element.
    
    # The mixing V comes from configuration interaction between 2G and 2H.
    # From group theory, V = 2*sqrt(6)*x (proportional to Dq).
    
    E_2G = 6 + 3*C_over_B
    E_2H = 6 + 3*C_over_B
    
    # 2Eg matrix
    H_2eg = np.array([[E_2G + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H - 3*x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g matrix
    H_2t1g = np.array([[E_2G - x, 2*x], 
                       [2*x, E_2H + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g matrix
    H_2t2g = np.array([[E_2G + x, x], 
                       [x, E_2H + 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

# Test the energies
print("Testing d3 energies:")
for dq_over_b in dq_over_b_values:
    levels = d3_energies(dq_over_b, C_over_B)
    print(f"Dq/B = {dq_over_b}: ground = {levels[0][1]} at E/B = {levels[0][0]:.4f}")
    if levels[0][1] != '4A2g':
        print(f"  WARNING: Ground state is {levels[0][1]}, not 4A2g!")

# The issue is clear: at high Dq/B, 2Eg becomes the ground state.
# This is WRONG for d3. The ground state should always be 4A2g.

# The problem is in the crystal field splitting coefficients.
# Let me check standard references for the correct coefficients.

# From "Introduction to Ligand Field Theory" (Ballhausen):
# For d3, the 2G and 2H terms have the following crystal field splittings:
# 2G: 2Eg at +2Dq, 2T1g at -Dq, 2T2g at +Dq (relative to 2G barycenter)
# 2H: 2Eg at +Dq, 2T1g at +Dq, 2T2g at -2Dq (relative to 2H barycenter)

# Wait, that's different from what I used! Let me try these coefficients.

print("\n\nUsing corrected crystal field splitting coefficients:")

def d3_energies_corrected(dq_over_b, C_over_B=4.094202898550725):
    x = dq_over_b
    levels = []
    
    # Quartets
    levels.append((0.0, '4A2g'))
    levels.append((10 * x, '4T2g'))
    
    H_4t1g = np.array([[18*x, 4*x], [4*x, 15 + 18*x]])
    eig_4t1g = np.linalg.eigvalsh(H_4t1g)
    levels.append((eig_4t1g[0], '4T1g'))
    levels.append((eig_4t1g[1], '4T1g'))
    
    # Doublets with corrected CF splitting
    E_2G = 6 + 3*C_over_B
    E_2H = 6 + 3*C_over_B
    
    # 2Eg: 2G at +2Dq, 2H at +Dq (corrected from -3Dq)
    H_2eg = np.array([[E_2G + 2*x, 2*np.sqrt(6)*x], 
                      [2*np.sqrt(6)*x, E_2H + x]])
    eig_2eg = np.linalg.eigvalsh(H_2eg)
    levels.append((eig_2eg[0], '2Eg'))
    levels.append((eig_2eg[1], '2Eg'))
    
    # 2T1g: 2G at -Dq, 2H at +Dq
    H_2t1g = np.array([[E_2G - x, 2*x], 
                       [2*x, E_2H + x]])
    eig_2t1g = np.linalg.eigvalsh(H_2t1g)
    levels.append((eig_2t1g[0], '2T1g'))
    levels.append((eig_2t1g[1], '2T1g'))
    
    # 2T2g: 2G at +Dq, 2H at -2Dq (corrected from +2Dq)
    H_2t2g = np.array([[E_2G + x, x], 
                       [x, E_2H - 2*x]])
    eig_2t2g = np.linalg.eigvalsh(H_2t2g)
    levels.append((eig_2t2g[0], '2T2g'))
    levels.append((eig_2t2g[1], '2T2g'))
    
    levels.sort(key=lambda x: x[0])
    ground_energy = levels[0][0]
    levels = [(e - ground_energy, label) for e, label in levels]
    
    return levels[:6]

print("\nWith corrected CF coefficients:")
for dq_over_b in dq_over_b_values:
    levels = d3_energies_corrected(dq_over_b, C_over_B)
    print(f"Dq/B = {dq_over_b}: ground = {levels[0][1]} at E/B = {levels[0][0]:.4f}")
    for i, (e, label) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {e:.4f}")
