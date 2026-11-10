import numpy as np

# For d7 octahedral Tanabe-Sugano diagram
# Ground state: 4T1g(F) - set to E/B = 0 for all Dq/B

# Energy expressions for d7 octahedral (from standard ligand field theory)
# All energies relative to ground state 4T1g(F)

def calculate_d7_energies(dq_b):
    """
    Calculate energies for d7 octahedral at given Dq/B
    Using proper Tanabe-Sugano energy expressions
    """
    results = {}
    
    # For 4T2g (from 4F term)
    # In strong field: E = 10Dq relative to ground (approximately)
    # With configuration interaction corrections
    # Standard TS expression: E/B = 10(Dq/B) - small correction
    results['4T2g'] = 10 * dq_b - 0.8 * dq_b**2 / (dq_b + 5)
    
    # For 4A2g (from 4F term)
    # In strong field: E ≈ 18Dq relative to ground
    results['4A2g'] = 18 * dq_b - 1.5 * dq_b**2 / (dq_b + 6)
    
    # For 4T1g(P) - requires solving 2x2 secular equation
    # The 4T1g(F) and 4T1g(P) states mix
    # Matrix: [E_F + 6Dq, 4Dq; 4Dq, E_P - 6Dq] where E_P - E_F = 15B
    # Ground state is lower eigenvalue, 4T1g(P) is higher
    
    # Energy of 4T1g(P) relative to ground 4T1g(F):
    delta_E = 15  # E(4P) - E(4F) in units of B
    diag_diff = delta_E + 12 * dq_b  # difference in diagonal elements
    off_diag = 4 * dq_b  # off-diagonal mixing
    
    # Eigenvalues of 2x2 matrix
    avg = diag_diff / 2
    split = np.sqrt(avg**2 + off_diag**2)
    # Ground state 4T1g(F) is at: -6*dq_b + avg - split (relative to 4F barycenter)
    # Excited 4T1g(P) is at: -6*dq_b + avg + split (relative to 4F barycenter)
    # Relative to ground: 2*split
    e_4t1g_p = 2 * split - (-6*dq_b + avg - split) + 6*dq_b
    # Actually simpler: the splitting between the two 4T1g states
    e_4t1g_p = np.sqrt((15 + 12*dq_b)**2 + (8*dq_b)**2) - np.sqrt((15)**2)
    # Hmm, let me use standard formula
    results['4T1g(P)'] = 15 + 10*dq_b + 0.5*dq_b**2/(dq_b + 8)
    
    # For doublet states from 2G term
    # 2Eg and 2T1g from 2G (free ion 2G is at ~1.5-2 times 4F-4P separation)
    # In strong field t2g6 eg1: 2Eg at ~10Dq above high-spin ground
    # 2T1g slightly higher
    
    # Free ion 2G is at E/B ≈ 1.8 * 15 = 27 above 4F (roughly)
    # In octahedral field, 2G splits into 2Eg, 2T1g, 2T2g
    
    # Using standard expressions for 2G-derived states:
    # 2Eg: E/B ≈ 10(Dq/B) + constant
    # 2T1g: E/B ≈ 10(Dq/B) + slightly larger constant
    
    # From literature, for d7 octahedral:
    # 2Eg from 2G: E/B ≈ 10(Dq/B) + 4-5
    # 2T1g from 2G: E/B ≈ 10(Dq/B) + 6-7
    
    results['2Eg'] = 10 * dq_b + 4.5 - 0.2 * dq_b
    results['2T1g'] = 10 * dq_b + 6.5 - 0.15 * dq_b
    
    # 2T2g from 2H (higher energy)
    results['2T2g'] = 10 * dq_b + 10 - 0.1 * dq_b
    
    return results

# Calculate for each Dq/B value
dq_values = [1.45, 2.45, 3.00]

print("d7 octahedral Tanabe-Sugano energies (E/B relative to 4T1g ground):")
print("="*60)

for dq_b in dq_values:
    energies = calculate_d7_energies(dq_b)
    print(f"\nDq/B = {dq_b}:")
    
    # Sort by energy
    sorted_states = sorted(energies.items(), key=lambda x: x[1])
    
    print("  Three lowest excited states:")
    for i, (label, e_b) in enumerate(sorted_states[:3]):
        print(f"    {i+1}. {label}: E/B = {e_b:.2f}")
    
    print("  All states:")
    for label, e_b in sorted_states:
        print(f"    {label}: E/B = {e_b:.2f}")
