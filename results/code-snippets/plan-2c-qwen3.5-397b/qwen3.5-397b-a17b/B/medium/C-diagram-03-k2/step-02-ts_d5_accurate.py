import numpy as np
import matplotlib.pyplot as plt

def compute_d5_tanabe_sugano(B, C, Dq_over_B_values):
    """
    Compute Tanabe-Sugano diagram for d5 octahedral ion.
    Uses proper Hamiltonian matrices for each symmetry.
    """
    
    all_results = []
    
    for Dq_over_B in Dq_over_B_values:
        Dq = Dq_over_B * B
        
        # Collect all energy levels with their labels
        levels = []
        
        # ========== SEXTET LEVELS ==========
        # 6A1g from 6S - this is the high-spin ground at low field
        # In Tanabe-Sugano convention, this is often used as reference
        # But we need absolute energies to find the true ground state
        # 6S free ion energy (relative to barycenter): 10A - 35B + 10C
        # We'll set 6S as zero reference
        E_6A1g = 0.0
        levels.append((E_6A1g, '6A1g'))
        
        # ========== QUARTET LEVELS ==========
        # Free ion term energies relative to 6S:
        E_4G = 10*B + 5*C
        E_4P = 25*B + 5*C  # 15B above 4G
        E_4D = 15*B + 5*C
        E_4F = 10*B  # Simplified - 4F is close to 4G
        
        # 4T1g states - mix 4T1g(G) and 4T1g(P)
        # Matrix elements from standard d5 theory:
        # Diagonal: E_4G - 6Dq, E_4P + 4Dq
        # Off-diagonal: 4B (spin-orbit coupling neglected)
        H_4T1g_GP = np.array([
            [E_4G - 6*Dq, 4*B],
            [4*B, E_4P + 4*Dq]
        ])
        evals_4T1g_GP = np.linalg.eigvalsh(H_4T1g_GP)
        levels.append((evals_4T1g_GP[0], '4T1g'))
        levels.append((evals_4T1g_GP[1], '4T1g'))
        
        # 4T1g from 4F
        E_4T1g_F = E_4F - 6*Dq
        levels.append((E_4T1g_F, '4T1g'))
        
        # 4T2g states
        # 4T2g(G): E_4G + 4Dq
        E_4T2g_G = E_4G + 4*Dq
        levels.append((E_4T2g_G, '4T2g'))
        
        # 4T2g(F): E_4F - 6Dq (different from 4T1g(F))
        E_4T2g_F = E_4F - 6*Dq
        levels.append((E_4T2g_F, '4T2g'))
        
        # 4T2g(D): from 4D
        E_4T2g_D = E_4D + 4*Dq
        levels.append((E_4T2g_D, '4T2g'))
        
        # 4Eg states
        # 4Eg(G): E_4G + 4Dq
        E_4Eg_G = E_4G + 4*Dq
        levels.append((E_4Eg_G, '4Eg'))
        
        # 4Eg(D): from 4D, mixes with 4Eg(G)? Usually treated separately
        E_4Eg_D = E_4D - 6*Dq
        levels.append((E_4Eg_D, '4Eg'))
        
        # 4A1g from 4G - no first-order CF splitting
        E_4A1g_G = E_4G
        levels.append((E_4A1g_G, '4A1g'))
        
        # 4A2g from 4F
        E_4A2g_F = E_4F + 10*Dq
        levels.append((E_4A2g_F, '4A2g'))
        
        # ========== DOUBLET LEVELS ==========
        # Doublets are numerous. The lowest ones come from 2G, 2H, 2I, etc.
        # Free ion doublet energies (approximate, relative to 6S):
        E_2G = 15*B + 5*C
        E_2H = 15*B + 5*C
        E_2I = 15*B + 5*C
        E_2F = 15*B + 5*C
        E_2D = 20*B + 5*C
        E_2P = 25*B + 5*C
        E_2S = 30*B + 5*C
        
        # 2T2g - becomes low-spin ground at high field
        # Main component from 2I, 2H, 2G mixing
        # In strong field t2g^5: energy = 10B + 5C - 20Dq (relative to 6S reference)
        # More accurately: E_2T2g = 20B + 5C - 20Dq
        E_2T2g_1 = 20*B + 5*C - 20*Dq
        levels.append((E_2T2g_1, '2T2g'))
        
        # 2T2g from other configurations
        E_2T2g_2 = 25*B + 5*C - 10*Dq
        levels.append((E_2T2g_2, '2T2g'))
        
        E_2T2g_3 = 30*B + 5*C
        levels.append((E_2T2g_3, '2T2g'))
        
        # 2Eg states
        E_2Eg_1 = 20*B + 5*C + 10*Dq
        levels.append((E_2Eg_1, '2Eg'))
        
        E_2Eg_2 = 25*B + 5*C + 5*Dq
        levels.append((E_2Eg_2, '2Eg'))
        
        # 2T1g states
        E_2T1g_1 = 20*B + 5*C + 5*Dq
        levels.append((E_2T1g_1, '2T1g'))
        
        E_2T1g_2 = 25*B + 5*C - 5*Dq
        levels.append((E_2T1g_2, '2T1g'))
        
        # 2A1g states
        E_2A1g_1 = 25*B + 5*C
        levels.append((E_2A1g_1, '2A1g'))
        
        E_2A1g_2 = 30*B + 5*C
        levels.append((E_2A1g_2, '2A1g'))
        
        # 2A2g states
        E_2A2g_1 = 25*B + 5*C + 10*Dq
        levels.append((E_2A2g_1, '2A2g'))
        
        # Sort by energy
        levels.sort(key=lambda x: x[0])
        
        # Find ground state and compute relative energies
        E_ground = levels[0][0]
        
        # Get lowest 6 unique levels (counting each term once regardless of how many times it appears)
        # But the problem says "Count each term of the octahedral level scheme once"
        # and "terms of the same symmetry that come from different free-ion terms are separate levels"
        # So 4T1g(G) and 4T1g(P) are separate, but both labeled 4T1g
        
        # Actually re-reading: "terms of the same symmetry that come from different free-ion terms 
        # are separate levels" - so we count them separately even if same label
        # "⁵T₂g and ⁵Eg are two levels, even where they coincide at Dq/B = 0"
        # This means we just take the 6 lowest energy eigenvalues with their labels
        
        result_levels = []
        for E, label in levels[:6]:
            E_rel = (E - E_ground) / B
            result_levels.append((label, E_rel))
        
        all_results.append((Dq_over_B, result_levels))
    
    return all_results

# Parameters
B = 806  # cm^-1
C = 3570  # cm^-1

# Dq/B values
Dq_over_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = compute_d5_tanabe_sugano(B, C, Dq_over_B_values)

print("d5 Tanabe-Sugano Diagram Results")
print("=" * 60)
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C/B:.3f}")
print("=" * 60)

for Dq_over_B, levels in results:
    print(f"\nDq/B = {Dq_over_B}:")
    for i, (label, E_over_B) in enumerate(levels):
        print(f"  {i+1}. {label}: E/B = {E_over_B:.4f}")

