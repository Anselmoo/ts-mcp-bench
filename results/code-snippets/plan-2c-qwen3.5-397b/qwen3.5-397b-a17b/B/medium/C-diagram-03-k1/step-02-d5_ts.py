"""
Tanabe-Sugano diagram for d5 octahedral ion.
Uses the complete d5 Hamiltonian in the weak-field basis.
"""

import numpy as np
import matplotlib.pyplot as plt

# Racah parameters
B = 806.0  # cm^-1
C = 3570.0  # cm^-1

# For d5, we need to construct the Hamiltonian matrix
# The free-ion terms and their energies (in units of B, with C/B ratio)
# Using standard formulas from ligand field theory

# Free ion term energies for d5 (relative to 6S ground state, in units of B)
# C/B = 3570/806 = 4.429
CB_ratio = C / B

# Term energies from standard d5 formulas (E/B values)
# Reference: "The Theory of Transition Metal Ions" by J.S. Griffith
# or "Ligand Field Theory" by Figgis

# For d5 configuration:
# 6S: E/B = 0
# 4G: E/B = 10 + 5*(C/B) - correction terms
# Actually, let me use the more accurate formulas

# From standard tables for d5:
# Using the formulas from Tanabe-Sugano original paper or subsequent work

def get_free_ion_energies(B, C):
    """
    Return free-ion term energies for d5 configuration.
    Energies in cm^-1 relative to 6S ground state.
    """
    # Using formulas from standard references
    # 6S is the ground state at E=0
    
    energies = {
        '6S': 0.0,
        '4G': 10*B + 5*C,  # Approximate
        '4P': 15*B + 5*C,  # Approximate  
        '4F': 7*B + 5*C,   # Approximate
        '4D': 12*B + 5*C,  # Approximate
    }
    return energies

# Actually, I need to be more careful here. Let me use a proper approach
# by constructing the full Hamiltonian.

# For d5 in Oh symmetry, the states are classified by their irreducible representations
# We need to handle:
# - Sextet states: 6A1g (from 6S)
# - Quartet states: from 4G, 4P, 4F, 4D
# - Doublet states: from various doublet free-ion terms

# The splitting patterns in Oh:
# 6S -> 6A1g
# 4G -> 4A1g + 4Eg + 4T1g + 4T2g  
# 4P -> 4T1g
# 4F -> 4A2g + 4T1g + 4T2g
# 4D -> 4Eg + 4T2g

# For the lowest 6 levels, we mainly need the sextet and quartet states
# (doublets are typically much higher in energy for moderate Dq)

# Let me use the analytical formulas for d5 energy levels

def d5_energies(Dq, B, C):
    """
    Calculate energy levels for d5 in octahedral field.
    Returns list of (energy, term_label) tuples.
    
    Uses formulas from standard Tanabe-Sugano treatment.
    """
    energies = []
    
    # === Sextet states (from 6S) ===
    # 6A1g: This is the high-spin ground state at low Dq
    # Energy = 0 (we set 6S as reference)
    # But in the crystal field, we need to account for the field splitting
    
    # For d5 high-spin (t2g^3 eg^2): 
    # The 6A1g energy relative to barycenter is 0 (no first-order CF splitting for S state)
    E_6A1g = 0.0
    energies.append((E_6A1g, '6A1g'))
    
    # === Quartet states ===
    # These come from 4G, 4P, 4F, 4D free ion terms
    
    # Free ion term energies (relative to 6S)
    E_4G = 10*B + 5*C
    E_4P = 15*B + 5*C  
    E_4F = 7*B + 5*C
    E_4D = 12*B + 5*C
    
    # In octahedral field, these split and mix
    # We need to diagonalize matrices for states of same symmetry
    
    # 4A1g and 4Eg from 4G (no mixing with other terms at first approximation)
    # 4A1g(4G): E = E_4G - 4*Dq (approximate, need proper formula)
    # Actually for 4G -> 4A1g + 4Eg in Oh:
    # The splitting is more complex
    
    # Let me use the proper weak-field formulas
    # For 4G term in Oh field:
    # The matrix elements involve Dq and the free ion energy
    
    # From standard references, the energies are:
    
    # 4T1g(4F): This comes from 4F term
    # At Dq=0: E = E_4F
    # With field: need to solve 2x2 matrix with 4T1g(4P)
    
    # 4T1g(4P): From 4P term
    # These two 4T1g states mix
    
    # 4T2g states: from 4G, 4F, 4D - three states mix
    
    # This is getting complex. Let me use a different approach -
    # use known formulas from the literature for d5
    
    # From "Inorganic Electronic Spectroscopy" by A.B.P. Lever:
    # For d5, the energy matrices are well documented
    
    # Let me implement the proper matrix diagonalization
    
    return energies

# Actually, let me use a more systematic approach with proper matrices
# Reference: "The Theory of Transition Metal Ions" by Griffith, Chapter on d5

print("Computing d5 Tanabe-Sugano diagram...")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C/B:.3f}")
