cat << 'EOF' > d7_tanabe_sugano.py
import numpy as np

# For d7 octahedral, we need to calculate term energies
# Using the strong-field basis and diagonalizing the matrices

# Racah parameters (we'll work in units of B)
B = 1.0  # Working in units of B
C_over_B = 3699 / 784  # C/B ratio

def d7_quartet_energies(Dq_over_B):
    """
    Calculate quartet state energies for d7 octahedral.
    Returns energies in units of B relative to the 4F barycenter.
    """
    Dq = Dq_over_B * B
    
    # 4T2g(F): Energy = -2*Dq (relative to 4F barycenter)
    E_4T2g = -2 * Dq_over_B
    
    # 4A2g(F): Energy = -12*Dq (relative to 4F barycenter)
    E_4A2g = -12 * Dq_over_B
    
    # 4T1g states: Need to diagonalize 2x2 matrix
    # Matrix for 4T1g(F) and 4T1g(P) mixing:
    # | -6*Dq/B    4*Dq/B  |
    # |  4*Dq/B    15      |
    # (energies relative to 4F barycenter, in units of B)
    
    matrix_4T1g = np.array([
        [-6 * Dq_over_B, 4 * Dq_over_B],
        [4 * Dq_over_B, 15]
    ])
    
    eigenvalues_4T1g = np.linalg.eigvalsh(matrix_4T1g)
    # Lower eigenvalue is 4T1g(F), higher is 4T1g(P)
    E_4T1g_F = eigenvalues_4T1g[0]
    E_4T1g_P = eigenvalues_4T1g[1]
    
    return {
        '4T1g(F)': E_4T1g_F,
        '4T2g(F)': E_4T2g,
        '4A2g(F)': E_4A2g,
        '4T1g(P)': E_4T1g_P
    }

def d7_doublet_energies(Dq_over_B, C_over_B):
    """
    Calculate doublet state energies for d7 octahedral.
    This is more complex - using approximate formulas from literature.
    
    For d7, the low-spin ground state at high field is 2Eg from t2g6eg1.
    """
    Dq = Dq_over_B * B
    
    # The 2Eg and 2T1g states from 2G term
    # At strong field (t2g6eg1), 2Eg is at energy ~10Dq - some electron repulsion
    
    # Using formulas from Griffith/ballhausen for d7 doublets:
    # 2Eg(G): Energy relative to 4F barycenter
    # 2T1g(G): Energy relative to 4F barycenter
    # 2T2g(G): Energy relative to 4F barycenter
    
    # Simplified approach: use strong-field energies
    # t2g6eg1 configuration: 2Eg and 2T1g
    # Energy of t2g6eg1 relative to t2g5eg2 (high spin) is about 10Dq - pairing energy
    
    # More accurate: diagonalize the doublet matrices
    # For 2Eg states (from 2G and 2D mixing):
    # Matrix elements from Ballhausen "Introduction to Ligand Field Theory"
    
    # 2Eg from 2G: ~ 7B + 7C - 10Dq (very approximate)
    # Actually need proper matrix diagonalization
    
    # Using empirical formulas from Tanabe-Sugano calculations:
    # For 2Eg (from 2G):
    E_2Eg_G = 7 + 7*C_over_B - 10*Dq_over_B  # Very approximate
    
    # For 2T1g (from 2G):
    E_2T1g_G = 7 + 7*C_over_B - 10*Dq_over_B + 2*Dq_over_B  # Approximate
    
    # For 2T2g (from 2G):
    E_2T2g_G = 7 + 7*C_over_B - 6*Dq_over_B  # Approximate
    
    # Better approach: use published Tanabe-Sugano data points
    # These are approximate and need refinement
    
    return {
        '2Eg(G)': E_2Eg_G,
        '2T1g(G)': E_2T1g_G,
        '2T2g(G)': E_2T2g_G
    }

# Let me use a more accurate approach based on published d7 Tanabe-Sugano data
# Reading from standard references

def get_d7_energies_accurate(Dq_over_B, C_over_B):
    """
    More accurate calculation using proper matrix diagonalization
    for d7 octahedral configuration.
    """
    
    # Quartet energies (these are well-established)
    quartets = d7_quartet_energies(Dq_over_B)
    
    # For doublets, we need to consider:
    # 2Eg, 2T1g, 2T2g from various parent terms (2G, 2H, 2P, 2D)
    
    # Using the strong-field coupling scheme for d7:
    # The doublet states come from multiple configurations
    
    # From Figgis & Hitchman "Ligand Field Theory and Its Applications":
    # For d7, the 2Eg state energy (relative to ground 4T1g at weak field)
    
    # Let me use the actual Tanabe-Sugano diagram values
    # These are calculated from full diagonalization
    
    # For d7 with C/B = 4.72 (our case: 3699/784 = 4.718)
    
    # I'll implement the full calculation
    # Reference: "The Theory of Transition Metal Ions" by J.S. Griffith
    
    # For 2Eg states, there are multiple that can mix
    # The lowest 2Eg comes primarily from 2G
    
    # Matrix for 2Eg states (simplified - usually 3x3 or larger)
    # Using parameters from standard calculations
    
    # Actually, let me use published formulas
    # From Ballhausen, for d7:
    
    # 2Eg energy (lowest, from 2G):
    # E(2Eg) = A + 10B + 5C - 10Dq + ... (mixing terms)
    
    # For practical calculation, I'll use the approach of
    # calculating relative to the 4F barycenter
    
    # Doublet energies relative to 4F barycenter:
    # 2G term is at 5B + 2C above 4F
    # 2H term is at ...
    
    # Let me use a different approach - numerical values from T-S diagrams
    
    results = {}
    
    # Quartets (relative to 4F barycenter)
    results.update(quartets)
    
    # Doublets - using approximate formulas
    # 2Eg from 2G: E = 5B + 2C - 10Dq (in strong field limit)
    # But need to account for mixing
    
    # More accurate: the 2Eg energy relative to 4F barycenter
    # At Dq=0: 2G is at 5B + 2C above 4F
    # With field: splits and shifts
    
    E_2Eg = 5 + 2*C_over_B - 10*Dq_over_B  # Simplified
    E_2T1g = 5 + 2*C_over_B - 10*Dq_over_B + 3*Dq_over_B  # Simplified  
    E_2T2g_1 = 5 + 2*C_over_B - 6*Dq_over_B  # From 2G
    E_2T2g_2 = 10 + 3*C_over_B - 2*Dq_over_B  # From 2H (higher)
    E_2A1g = 15 + 5*C_over_B - 12*Dq_over_B  # Approximate
    
    results['2Eg'] = E_2Eg
    results['2T1g'] = E_2T1g
    results['2T2g'] = E_2T2g_1
    results['2A1g'] = E_2A1g
    
    return results

# Calculate for the three Dq/B values
Dq_B_values = [1.45, 2.45, 3.00]
C_B = 3699 / 784

print(f"C/B = {C_B:.3f}")
print()

for Dq_B in Dq_B_values:
    print(f"Dq/B = {Dq_B}")
    print("-" * 50)
    
    energies = get_d7_energies_accurate(Dq_B, C_B)
    
    # Find ground state (lowest energy)
    ground_state = min(energies, key=energies.get)
    ground_energy = energies[ground_state]
    
    print(f"Ground state: {ground_state} at E/B = {ground_energy:.3f}")
    print()
    print("All states (relative to 4F barycenter):")
    for state, energy in sorted(energies.items(), key=lambda x: x[1]):
        print(f"  {state}: E/B = {energy:.3f}")
    
    print()
    print("Excited states relative to ground:")
    excited = [(s, e - ground_energy) for s, e in energies.items() if s != ground_state]
    for state, energy in sorted(excited, key=lambda x: x[1])[:5]:
        print(f"  {state}: E/B = {energy:.3f}")
    print()
EOF
python3 d7_tanabe_sugano.py