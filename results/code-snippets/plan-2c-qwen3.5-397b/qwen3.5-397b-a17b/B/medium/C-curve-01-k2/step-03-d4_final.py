"""
Final d4 Tanabe-Sugano calculation with refined parameters.
"""

import numpy as np

B = 821
C = 3657
C_over_B = C / B  # 4.454

def d4_energies_refined(Dq_over_B, C_over_B=4.454):
    """
    Refined calculation for d4 Tanabe-Sugano energies.
    """
    Dq = Dq_over_B
    
    # Free ion term energies relative to 5D (in units of B)
    # For d4 with C/B = 4.454:
    E_3F_free = 15 - 0.6 * C_over_B  # ≈ 12.33
    E_3P_free = 15.0
    
    # Quintet states (from 5D):
    E_5Eg = -6 * Dq
    E_5T2g = 4 * Dq
    
    # 3T1g states: Mix 3F-derived and 3P-derived, plus low-spin t2g^4 contribution
    # 3F-derived 3T1g (before 3P mixing): E = E(3F) - 6Dq
    E_3T1g_3F = E_3F_free - 6 * Dq
    
    # Mix with 3P:
    H_3T1g = np.array([[E_3T1g_3F, 4.0], [4.0, E_3P_free]])
    E_3T1g_eig = np.linalg.eigvalsh(H_3T1g)
    E_3T1g_HS = E_3T1g_eig[0]  # Lower (3F-derived)
    E_3T1g_P = E_3T1g_eig[1]    # Higher (3P-derived)
    
    # Low-spin 3T1g from t2g^4:
    # Pairing energy P ≈ 22B for d4 (gives crossover at Dq/B ≈ 2.2)
    E_pair = 22.0
    E_3T1g_LS = -16 * Dq + E_pair
    
    # The actual 3T1g is the lower of HS-derived and LS-derived
    E_3T1g = min(E_3T1g_HS, E_3T1g_LS)
    
    # 3T2g: from 3F (HS) or t2g^4 (LS)
    E_3T2g_HS = E_3F_free + 2 * Dq
    E_3T2g_LS = -16 * Dq + E_pair + 6.0
    E_3T2g = min(E_3T2g_HS, E_3T2g_LS)
    
    # 3A2g: from 3F (HS) or t2g^4 (LS)
    E_3A2g_HS = E_3F_free + 12 * Dq
    E_3A2g_LS = -16 * Dq + E_pair + 16.0
    E_3A2g = min(E_3A2g_HS, E_3A2g_LS)
    
    # Compile states
    states = {
        '5Eg': E_5Eg,
        '5T2g': E_5T2g,
        '3T1g': E_3T1g,
        '3T2g': E_3T2g,
        '3A2g': E_3A2g,
    }
    
    # Find ground and compute relative energies
    ground = min(states, key=states.get)
    E_ground = states[ground]
    relative = {k: v - E_ground for k, v in states.items()}
    sorted_states = sorted(relative.items(), key=lambda x: x[1])
    
    return ground, sorted_states

# Calculate for each Dq/B
print("d4 Tanabe-Sugano energies (C/B = 4.454)")
print("=" * 60)

for Dq_B in [0.90, 2.15, 3.35]:
    ground, sorted_states = d4_energies_refined(Dq_B, C_over_B)
    print(f"\nDq/B = {Dq_B}:")
    print(f"  Ground state: {ground}")
    print(f"  Three lowest excited states:")
    for i, (term, E_rel) in enumerate(sorted_states[1:4], 1):
        print(f"    {i}. {term}: E/B = {E_rel:.2f}")
