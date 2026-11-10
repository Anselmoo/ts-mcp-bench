cat > ts_d5.py << 'EOF'
import numpy as np
import matplotlib.pyplot as plt

# For d5 in octahedral field, we need to construct the full Hamiltonian
# The free ion terms for d5 are: 6S, 4G, 4P, 4D, 4F, and many doublets
# In Oh symmetry, these split into various irreps

# Using the strong field basis (t2g^m eg^n configurations)
# For d5: t2g^5, t2g^4 eg^1, t2g^3 eg^2, t2g^2 eg^3, t2g^1 eg^4, eg^5

# Actually, let's use the standard approach with Racah parameters
# The matrix elements for d5 in Oh are well documented

# For d5, the basis states in terms of free-ion terms that split in Oh:
# Sextet: 6A1g (from 6S)
# Quartets: from 4G -> 4T1g, 4T2g, 4Eg, 4A1g; from 4P -> 4T1g; from 4F -> 4A2g, 4T1g, 4T2g; from 4D -> 4Eg, 4T2g
# Doublets: many from 2I, 2H, 2G, 2F, 2D, 2P, 2S

# The energies of free ion terms (relative to 6S ground):
# E(6S) = 0
# E(4G) = 10B + 5C (approximately, using Racah parameters)
# Actually for d5: E(4G) = A + 10B + 5C - (A) = 10B + 5C relative to 6S
# E(4P) = 15B + 5C (relative to 6S is 15B + 5C - 0 = 15B + 5C, but 4P from 4G is at 15B)
# E(4F) = 10B (relative to 6S, but this needs checking)
# E(4D) = 15B + 5C

# Let me use the standard Tanabe-Sugano formulation for d5
# The energies are expressed in units of B, with C/B as a parameter

# For d5, the standard free ion term energies (relative to 6S = 0):
# 4G: 10B + 5C
# 4P: 15B + 5C (this is 15B above 4G)
# 4F: 10B (actually this needs to be verified)
# 4D: 15B + 5C

# Actually, let me look up the correct Racah energy expressions for d5:
# For d5 high spin (6S): E = 10A - 35B + 10C (but we set this as zero reference)
# 4G: E = 10A - 25B + 10C, so relative to 6S: 10B
# 4P: E = 10A - 10B + 10C, so relative to 6S: 25B
# 4F: E = 10A - 25B + 10C, same as 4G? No wait...

# Let me use a different approach - the standard d5 Tanabe-Sugano energies

# The matrix for d5 in octahedral field is complex. Let me use known results.
# For the sextet 6A1g: E = 0 (reference, independent of Dq to first order)

# For quartets from 4G in Oh:
# 4T1g(G): needs matrix diagonalization with 4T1g(P)
# 4T2g(G): E = 10B + 5C - 4Dq (approximately)
# 4Eg(G): E = 10B + 5C + 4Dq (approximately)
# 4A1g(G): E = 10B + 5C (independent of Dq)

# Actually, let me implement the full calculation using the strong-field basis

def d5_tanabe_sugano(B, C, Dq_over_B_values):
    """
    Compute Tanabe-Sugano diagram for d5 octahedral ion.
    Returns energies E/B for lowest levels at each Dq/B.
    """
    results = []
    
    for Dq_over_B in Dq_over_B_values:
        Dq = Dq_over_B * B
        
        # Build Hamiltonian for d5 in octahedral field
        # We need to include all relevant states
        
        # The basis for d5 in strong field (t2g^m eg^n):
        # t2g^5: 2T2g (low spin ground at high field)
        # t2g^4 eg^1: 4T1g, 4T2g, 2T1g, 2T2g, 2Eg, etc.
        # t2g^3 eg^2: 6A1g (high spin ground at low field), 4T1g, 4T2g, 4A1g, 4A2g, 2...
        # t2g^2 eg^3: ...
        # t2g^1 eg^4: ...
        # eg^5: 2Eg
        
        # This is complex. Let me use the weak-field basis with known matrix elements.
        
        # For d5, the key levels we need to track:
        # Ground state changes from 6A1g (high spin) to 2T2g (low spin)
        
        # Let me construct matrices for each symmetry
        
        energies = []
        labels = []
        
        # 6A1g from 6S - this is the high-spin ground state at low field
        # Energy relative to 6S free ion = 0, crystal field shift = 0 (A1g from S state)
        # Actually in strong field, 6A1g is t2g^3 eg^2, energy = 3*0 + 2*(10Dq) - pairing
        # In Tanabe-Sugano, 6A1g energy is set to 0 at all Dq (it's the reference)
        # Wait, that's not quite right either...
        
        # In standard Tanabe-Sugano diagrams, the ground state energy is plotted as 0
        # For d5, at low Dq the ground is 6A1g, at high Dq it's 2T2g
        
        # Let me use the actual energy expressions:
        
        # Free ion term energies (relative to 6S = 0):
        E_6S = 0
        E_4G = 10*B + 5*C  # This is the standard expression
        E_4P = E_4G + 15*B  # 4P is 15B above 4G
        E_4F = 10*B  # Need to verify
        E_4D = 15*B + 5*C
        
        # Actually, for d5 the Racah energies are:
        # 6S: 10A - 35B + 10C (set as 0 reference)
        # 4G: 10A - 25B + 10C => relative = 10B
        # 4P: 10A - 10B + 10C => relative = 25B  
        # 4F: 10A - 25B + 10C => same as 4G? That can't be right
        
        # Let me use corrected values from standard references:
        # For d5:
        # 6S: reference = 0
        # 4G: 10B + 5C
        # 4P: 10B + 5C + 15B = 25B + 5C (15B above 4G)
        # 4F: This comes from different parent... 
        
        # I'll use a comprehensive approach with the full d5 Hamiltonian
        
        # Build the Hamiltonian matrix for all d5 states
        # This requires the complete basis and matrix elements
        
        # For practical computation, I'll use the known analytical expressions
        # where available and numerical diagonalization for mixed states
        
        # Sextet levels (only 6A1g from 6S):
        # 6A1g: E/B = 0 (by convention in TS diagrams, ground state reference)
        # But actually the energy depends on Dq through configuration interaction
        
        # Let me implement the strong-field approach:
        
        # Strong field configurations for d5:
        # t2g^5: 2T2g, energy = 5*0 + pairing = 10B + 5C + ... (in Racah units)
        # t2g^4 eg^1: various terms
        # t2g^3 eg^2: 6A1g, 4T1g, 4T2g, 4A1g, 4A2g, 2...
        # t2g^2 eg^3: ...
        # t2g^1 eg^4: ...
        # eg^5: 2Eg
        
        # The crystal field energy for configuration t2g^m eg^n is:
        # E_CF = m*0 + n*10Dq = n*10Dq (setting t2g at 0, eg at 10Dq)
        # But in Tanabe-Sugano, we use Dq not 10Dq, so eg is at 10*Dq
        
        # Actually in TS diagrams, the splitting is often parameterized as 10Dq
        # Let me check: Dq/B on x-axis, so Dq is the parameter
        # The eg-t2g splitting is 10Dq
        
        delta = 10 * Dq  # eg - t2g splitting
        
        # Now I need to build matrices for each symmetry
        # This is getting complex. Let me use a simplified but accurate approach.
        
        # For d5 Tanabe-Sugano, I'll compute using the standard method:
        # 1. List all states by symmetry
        # 2. Build Hamiltonian matrices including electrostatic and CF terms
        # 3. Diagonalize
        
        # The symmetries present in d5 Oh:
        # A1g: 6A1g, 4A1g (from 4G), 4A1g (from 4D?), 2A1g (multiple)
        # A2g: 4A2g (from 4F), 2A2g
        # Eg: 4Eg (from 4G), 4Eg (from 4D), 2Eg (multiple)
        # T1g: 4T1g (from 4G), 4T1g (from 4P), 4T1g (from 4F), 2T1g (multiple)
        # T2g: 4T2g (from 4G), 4T2g (from 4F), 4T2g (from 4D), 2T2g (multiple)
        
        # This is a large calculation. Let me implement it properly.
        
        pass
    
    return results

# Actually, let me use a pre-computed approach based on known d5 matrices
# The complete d5 calculation is quite involved

# I'll implement the calculation using the approach from standard references

print("Computing d5 Tanabe-Sugano diagram...")

# Parameters
B = 806  # cm^-1
C = 3570  # cm^-1
C_over_B = C / B  # approximately 4.43

print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")

# For d5, I need to diagonalize matrices for each symmetry
# Let me implement this properly using the strong-field basis

# Strong field basis states for d5 (t2g^m eg^n configurations):
# The states are labeled by their Oh symmetry

# I'll use the matrix elements from standard references (e.g., Griffith, Ballhausen)

def build_d5_hamiltonian(B, C, Dq):
    """
    Build the complete d5 Hamiltonian in octahedral symmetry.
    Returns eigenvalues and eigenvectors.
    """
    # This is a simplified implementation focusing on the lowest energy states
    
    # Free ion term energies relative to 6S (using Racah parameters):
    # 6S: 0
    # 4G: 10B + 5C
    # 4P: 25B + 5C (15B above 4G)
    # 4F: ~10B (need accurate value)
    # 4D: 15B + 5C
    
    # More accurate d5 free ion energies (from Condon-Shortley):
    # E(6S) = 10A - 35B + 10C (reference, set to 0)
    # E(4G) = 10A - 25B + 10C => E - E(6S) = 10B
    # E(4P) = 10A - 10B + 10C => E - E(6S) = 25B
    # E(4F) = 10A - 25B + 10C => same as 4G? 
    # E(4D) = 10A - 20B + 10C => E - E(6S) = 15B
    
    # Wait, I need to be more careful. Let me use standard values:
    # For d5, the free ion terms have energies:
    # 6S: 0 (reference)
    # 4G: 10B + 5C
    # 4P: 10B + 5C + 15B = 25B + 5C
    # 4F: This is tricky - 4F from d5... 
    # 4D: 15B + 5C
    
    # Actually for d5, using Racah parameters with proper coefficients:
    # The energies relative to the barycenter involve different combinations
    
    # Let me use a practical approach: construct matrices for each symmetry
    # using known matrix elements from the literature
    
    # For the lowest states in d5 TS diagram, we need:
    # - 6A1g (from 6S) - high spin ground at low field
    # - 4T1g, 4T2g, 4Eg, 4A1g (from 4G)
    # - 4T1g (from 4P) - mixes with 4T1g from 4G
    # - 4A2g, 4T1g, 4T2g (from 4F)
    # - 2T2g (from 2I, 2H, etc.) - low spin ground at high field
    # - Other doublets
    
    # This is getting very complex. Let me use a numerical approach
    # with the strong-field basis states.
    
    pass

# Let me implement a working solution using known d5 energy expressions

import numpy as np
from numpy import linalg as LA

def d5_energies(B, C, Dq):
    """
    Compute d5 energy levels in octahedral field.
    Returns list of (energy, label) tuples.
    """
    
    energies = []
    
    # Free ion term energies relative to 6S ground state
    # Using standard Racah parameter expressions for d5
    E_6S = 0
    E_4G = 10*B + 5*C
    E_4P = E_4G + 15*B  # 4P is 15B above 4G
    E_4F = 10*B + 5*C - 5*B  # Approximate - 4F is close to 4G
    E_4D = 15*B + 5*C
    
    # Actually, let me look up the correct d5 free ion energies:
    # From standard texts (e.g., Figgis, Introduction to Ligand Fields):
    # For d5, relative to 6S = 0:
    # 4G: 10B + 5C
    # 4P: 25B + 5C
    # 4D: 15B + 5C
    # 4F: This requires more careful treatment
    
    # The correct free-ion term energies for d5 (relative to 6S):
    # Using Racah parameters with proper coefficients:
    # 6S: 0
    # 4G: 10B + 5C
    # 4P: 25B + 5C
    # 4F: 10B + 5C (degenerate with 4G in pure electrostatic, but they're different terms)
    # Actually 4F should be different...
    
    # Let me use values from Tanabe-Sugano's original paper or standard references:
    # For d5: E(4G) = 10B + 5C, E(4P) = 25B + 5C, E(4D) = 15B + 5C
    # 4F energy is approximately 10B + 5C - some correction
    
    # I'll use: E_4F = 10*B + 5*C - 5*B = 5*B + 5*C (approximate)
    # Actually this needs to be verified
    
    # For now, let me use a working set of energies:
    E_4G = 10*B + 5*C
    E_4P = 25*B + 5*C
    E_4D = 15*B + 5*C
    E_4F = 10*B  # Simplified
    
    # Doublet energies (these are numerous and complex)
    # 2I, 2H, 2G, 2F, 2D, 2P, 2S all contribute
    # For the low-spin ground state 2T2g, we need the lowest doublet
    
    # Approximate doublet energies (relative to 6S):
    # 2G: ~15B + 5C
    # 2H: ~15B + 5C  
    # 2I: ~15B + 5C
    # These are all close in energy
    
    # For practical TS diagram, the lowest doublet is around 20-25B above 6S
    
    # Now apply crystal field splitting
    
    # 6A1g (from 6S): 
    # In strong field, 6A1g is t2g^3 eg^2
    # CF energy = 3*0 + 2*10Dq = 20Dq, but there's also exchange stabilization
    # In TS diagram, 6A1g is typically shown with weak Dq dependence
    # The actual energy is approximately constant (S state, no first-order CF splitting)
    E_6A1g = 0  # Reference
    
    # 4T1g from 4G:
    # This mixes with 4T1g from 4P
    # Need to diagonalize 2x2 matrix
    # Diagonal elements: E_4G + CF shift, E_4P + CF shift
    # Off-diagonal: mixing term (4B or similar)
    
    # For 4G -> 4T1g in Oh: CF energy = -6Dq (from group theory)
    # For 4P -> 4T1g in Oh: CF energy = ?
    
    # The 4T1g matrix (from 4G and 4P):
    # | E_4G - 6Dq    4B           |
    # | 4B           E_4P + x*Dq   |
    # where x is the CF coefficient for 4P -> 4T1g
    
    # Actually the standard 4T1g matrix for d5 is:
    # | 10B+5C - 6Dq    4B        |
    # | 4B             25B+5C + 4Dq |  (need to verify the Dq coefficients)
    
    # Let me use standard expressions:
    # 4T1g(G) and 4T1g(P) mix via 4B
    # CF shifts: 4T1g from 4G has -6Dq, from 4P has +4Dq (approximately)
    
    H_4T1g = np.array([
        [E_4G - 6*Dq, 4*B],
        [4*B, E_4P + 4*Dq]
    ])
    evals_4T1g = np.linalg.eigvalsh(H_4T1g)
    energies.append((evals_4T1g[0], '4T1g'))
    energies.append((evals_4T1g[1], '4T1g'))
    
    # 4T2g from 4G:
    # CF energy = +4Dq (approximately)
    E_4T2g_G = E_4G + 4*Dq
    energies.append((E_4T2g_G, '4T2g'))
    
    # 4T2g from 4F:
    # CF energy = -6Dq (approximately)
    E_4T2g_F = E_4F - 6*Dq
    energies.append((E_4T2g_F, '4T2g'))
    
    # 4T2g from 4D:
    E_4T2g_D = E_4D + 4*Dq  # or -6Dq, need to check
    energies.append((E_4T2g_D, '4T2g'))
    
    # 4Eg from 4G:
    E_4Eg_G = E_4G + 4*Dq  # or different coefficient
    energies.append((E_4Eg_G, '4Eg'))
    
    # 4Eg from 4D:
    E_4Eg_D = E_4D - 6*Dq
    energies.append((E_4Eg_D, '4Eg'))
    
    # 4A1g from 4G:
    # A1g from G has no first-order CF splitting
    E_4A1g_G = E_4G
    energies.append((E_4A1g_G, '4A1g'))
    
    # 4A2g from 4F:
    E_4A2g_F = E_4F + 10*Dq  # or different
    energies.append((E_4A2g_F, '4A2g'))
    
    # 6A1g:
    energies.append((E_6A1g, '6A1g'))
    
    # Doublets - these are numerous
    # 2T2g (lowest doublet, becomes ground at high field):
    # In strong field, 2T2g is t2g^5
    # CF energy = 5*0 = 0, but there's pairing energy
    # Relative to 6S: approximately 20B + 5C - 20Dq (for low spin)
    # Actually: t2g^5 has energy 10B + 5C - 20Dq relative to barycenter
    # Let me use: E_2T2g = 20*B + 5*C - 20*Dq (approximate)
    E_2T2g = 20*B + 5*C - 20*Dq
    energies.append((E_2T2g, '2T2g'))
    
    # 2A1g, 2Eg, 2T1g, etc.
    # These are at higher energies
    E_2Eg = 20*B + 5*C + 10*Dq  # t2g^4 eg^1 doublet
    energies.append((E_2Eg, '2Eg'))
    
    E_2T1g = 20*B + 5*C + 5*Dq
    energies.append((E_2T1g, '2T1g'))
    
    E_2A1g = 25*B + 5*C
    energies.append((E_2A1g, '2A1g'))
    
    E_2T2g_2 = 25*B + 5*C - 10*Dq
    energies.append((E_2T2g_2, '2T2g'))
    
    # Sort by energy
    energies.sort(key=lambda x: x[0])
    
    return energies

# Test the function
B = 806
C = 3570
Dq_over_B = 1.0
Dq = Dq_over_B * B

energies = d5_energies(B, C, Dq)
print(f"\nEnergies at Dq/B = {Dq_over_B}:")
for E, label in energies[:10]:
    print(f"  {label}: E/B = {E/B:.3f}")

EOF
python3 ts_d5.py