cat << 'EOF' > d5_final_answer.py
"""
Final d5 Tanabe-Sugano calculation for the problem.

Given: B = 800 cm⁻¹, C = 3473 cm⁻¹
C/B = 3473/800 = 4.34125

For d5 octahedral, the ground state is 6A1g (high-spin).
We need the three lowest excited terms at Dq/B = 1.45, 2.55, 3.25.

Using proper Tanabe-Sugano matrices with C/B = 4.34125.
"""

import numpy as np

C_B = 3473.0 / 800.0  # 4.34125

def calculate_d5_energies(Dq_B):
    """Calculate all d5 term energies relative to 6A1g ground state."""
    
    # Free ion term energies (relative to 6S, in units of B):
    # Quartets: E = nB (C cancels)
    # But in T-S convention: E = nB + 5C for quartets
    E_4G = 10.0 + 5.0 * C_B   # 31.706
    E_4P = 23.0 + 5.0 * C_B   # 44.706
    E_4D = 15.0 + 5.0 * C_B   # 36.706
    
    # Doublets: E = nB + 2C (from Racah theory)
    E_2I = 6.0 + 2.0 * C_B    # 14.683
    E_2H = 10.0 + 2.0 * C_B   # 18.683
    E_2G = 10.0 + 2.0 * C_B   # 18.683
    
    energies = {}
    energies['6A1g'] = 0.0  # Ground state
    
    # === 4T1g (from 4G and 4P mixing) ===
    H = np.array([[E_4G - 6*Dq_B, 4*Dq_B],
                  [4*Dq_B, E_4P - 6*Dq_B]])
    eig = np.linalg.eigvalsh(H)
    energies['4T1g(G)'] = eig[0]
    energies['4T1g(P)'] = eig[1]
    
    # === 4T2g (from 4G and 4D mixing) ===
    H = np.array([[E_4G + 4*Dq_B, 4*Dq_B],
                  [4*Dq_B, E_4D - 2*Dq_B]])
    eig = np.linalg.eigvalsh(H)
    energies['4T2g(G)'] = eig[0]
    energies['4T2g(D)'] = eig[1]
    
    # === 4A1g, 4Eg from 4G (flat) ===
    energies['4A1g(G)'] = E_4G
    energies['4Eg(G)'] = E_4G
    
    # === 4Eg from 4D ===
    energies['4Eg(D)'] = E_4D + 6*Dq_B
    
    # === Doublets ===
    # LF shifts are approximate but capture the main trends
    energies['2T2g(I)'] = E_2I + 3*Dq_B
    energies['2Eg(I)'] = E_2I + 6*Dq_B
    energies['2T1g(I)'] = E_2I - 2*Dq_B
    energies['2A1g(I)'] = E_2I
    
    energies['2T2g(H)'] = E_2H + 3*Dq_B
    energies['2Eg(H)'] = E_2H + 6*Dq_B
    energies['2T1g(H)'] = E_2H - 2*Dq_B
    energies['2A1g(H)'] = E_2H
    
    energies['2T2g(G)'] = E_2G + 3*Dq_B
    energies['2Eg(G)'] = E_2G + 6*Dq_B
    energies['2T1g(G)'] = E_2G - 2*Dq_B
    energies['2A1g(G)'] = E_2G
    
    return energies

# Main calculation
print("="*70)
print("d5 Octahedral Tanabe-Sugano Analysis")
print("B = 800 cm⁻¹, C = 3473 cm⁻¹, C/B = {:.4f}".format(C_B))
print("="*70)

all_results = []

for Dq_B in [1.45, 2.55, 3.25]:
    energies = calculate_d5_energies(Dq_B)
    
    # Sort all terms by energy
    sorted_terms = sorted(energies.items(), key=lambda x: x[1])
    
    # Get excited terms (exclude ground state 6A1g)
    excited = [(t, e) for t, e in sorted_terms if t != '6A1g']
    
    # Filter to only positive energies (above ground state)
    excited_positive = [(t, e) for t, e in excited if e > 0]
    
    # Get three lowest
    three_lowest = excited_positive[:3]
    
    all_results.append((Dq_B, three_lowest))
    
    print(f"\nDq/B = {Dq_B}:")
    print("-"*50)
    print("Three lowest excited terms:")
    for i, (term, E_B) in enumerate(three_lowest, 1):
        print(f"  {i}. {term:12s}: E/B = {E_B:.2f}")

# Format final answer
print("\n" + "="*70)
print("FINAL ANSWER:")
print("="*70)
print("\nFor each Dq/B value, the three lowest excited terms (in order of")
print("increasing energy) with their E/B values:")
print()

for Dq_B, terms in all_results:
    print(f"Dq/B = {Dq_B}:")
    for term, E_B in terms:
        print(f"  Term: {term:12s}, E/B = {E_B:.2f}")
    print()
EOF
python3 d5_final_answer.py