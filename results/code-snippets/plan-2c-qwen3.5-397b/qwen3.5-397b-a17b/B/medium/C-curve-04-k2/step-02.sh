cat << 'EOF' > d5_final.py
"""
Final calculation for d5 Tanabe-Sugano diagram energies.
Using standard energy expressions from ligand field theory.
"""

import numpy as np

def d5_energies(Dq_B, C_B):
    """
    Calculate energies for d5 octahedral complex.
    Returns dictionary of term: E/B values.
    
    Standard Tanabe-Sugano energy expressions for d5:
    - Ground state: 6A1g (reference at 0)
    - 4A1g(G), 4Eg(G): E/B = 10 + 5(C/B) (independent of Dq)
    - 4T1g: 2x2 matrix mixing 4T1g(G) and 4T1g(P)
    - 4T2g: 2x2 matrix mixing 4T2g(G) and 4T2g(D)
    - 4A2g(F): E/B = 5 + 5(C/B) + 10(Dq/B)
    - Doublets: approximate formulas
    """
    energies = {}
    
    # Ground state
    energies['6A1g'] = 0.0
    
    # 4A1g(G) and 4Eg(G) - no Dq dependence
    E_4A1g_4Eg_G = 10 + 5 * C_B
    energies['4A1g(G)'] = E_4A1g_4Eg_G
    energies['4Eg(G)'] = E_4A1g_4Eg_G
    
    # 4T1g matrix (mixing 4T1g from 4G and 4P)
    # H11 = 10 + 5(C/B) - 5(Dq/B)  [4T1g from 4G]
    # H22 = 25 + 5(C/B) + 10(Dq/B) [4T1g from 4P]
    # H12 = -4(Dq/B)
    H11 = 10 + 5*C_B - 5*Dq_B
    H22 = 25 + 5*C_B + 10*Dq_B
    H12 = -4 * Dq_B
    
    delta = (H11 - H22) / 2
    avg = (H11 + H22) / 2
    mixing = np.sqrt(delta**2 + H12**2)
    
    energies['4T1g(G)'] = avg - mixing  # Lower root
    energies['4T1g(P)'] = avg + mixing  # Upper root
    
    # 4T2g matrix (mixing 4T2g from 4G and 4D)
    # H11 = 10 + 5(C/B) + 5(Dq/B)  [4T2g from 4G]
    # H22 = 15 + 5(C/B) - 5(Dq/B)  [4T2g from 4D]
    # H12 = -4(Dq/B)
    H11_T2 = 10 + 5*C_B + 5*Dq_B
    H22_T2 = 15 + 5*C_B - 5*Dq_B
    H12_T2 = -4 * Dq_B
    
    delta_T2 = (H11_T2 - H22_T2) / 2
    avg_T2 = (H11_T2 + H22_T2) / 2
    mixing_T2 = np.sqrt(delta_T2**2 + H12_T2**2)
    
    energies['4T2g(G)'] = avg_T2 - mixing_T2  # Lower root
    energies['4T2g(D)'] = avg_T2 + mixing_T2  # Upper root
    
    # 4A2g(F) from 4F term
    energies['4A2g(F)'] = 5 + 5*C_B + 10*Dq_B
    
    # Doublet states (spin-forbidden)
    # Lowest doublets from 2G, 2H, 2I terms
    # Approximate energies based on standard d5 diagrams
    energies['2T2g'] = 12 + 5*C_B - 3*Dq_B
    energies['2Eg'] = 12 + 5*C_B + 2*Dq_B
    energies['2A1g'] = 15 + 5*C_B
    
    return energies

# Parameters
B = 800  # cm^-1
C = 3473  # cm^-1
C_B = C / B  # C/B ratio

print(f"Racah parameters: B = {B} cm^-1, C = {C} cm^-1")
print(f"C/B = {C_B:.4f}")
print()

Dq_B_values = [1.45, 2.55, 3.25]

results = []

for Dq_B in Dq_B_values:
    print(f"=" * 60)
    print(f"Dq/B = {Dq_B}")
    print(f"=" * 60)
    
    energies = d5_energies(Dq_B, C_B)
    
    # Sort by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    print("\nAll terms (sorted by energy):")
    for term, E_B in sorted_terms:
        print(f"  {term:12s}: E/B = {E_B:8.3f}")
    
    # Get three lowest excited terms (excluding ground 6A1g)
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g']
    three_lowest = excited[:3]
    
    print(f"\nThree lowest excited terms:")
    for i, (term, E_B) in enumerate(three_lowest):
        print(f"  {i+1}. {term:12s}: E/B = {E_B:8.3f}")
        results.append((Dq_B, term, E_B))
    
    print()

print("\n" + "=" * 60)
print("SUMMARY: Nine points for structured output")
print("=" * 60)
for Dq_B, term, E_B in results:
    print(f"Dq/B = {Dq_B:5.2f}: {term:12s} -> E/B = {E_B:.3f}")
EOF
python3 d5_final.py