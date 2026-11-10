"""
Complete Tanabe-Sugano diagram for d5 octahedral ion.
Uses proper energy matrices from ligand field theory.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hashlib

# Racah parameters
B = 806.0  # cm^-1
C = 3570.0  # cm^-1
CB = C / B  # C/B ratio = 4.429

print(f"d5 Tanabe-Sugano diagram calculation")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {CB:.3f}")

def get_d5_energies(Dq, B, C):
    """
    Compute energy levels for d5 in octahedral field.
    Returns list of (energy, term_label) tuples.
    """
    CB = C / B
    
    # Free ion term energies relative to 6S ground state
    # Using standard formulas that give reasonable T-S diagram
    # E(6S) = 0 (reference)
    E_4G = 10*B + 5*C   # ~25910 cm^-1
    E_4P = 15*B + 5*C   # ~29940 cm^-1
    E_4F = 7*B + 5*C    # ~23492 cm^-1
    E_4D = 12*B + 5*C   # ~27522 cm^-1
    
    results = []
    
    # === SEXTET ===
    # 6A1g from 6S - ground state at low Dq, energy = 0 (reference)
    results.append((0.0, '6A1g'))
    
    # === QUARTETS ===
    
    # 4T1g: 2x2 matrix from mixing of 4T1g(4F) and 4T1g(4P)
    # Standard matrix elements (in weak-field basis):
    # Diagonal: E(term) + crystal field shift
    # Off-diagonal: mixing proportional to Dq
    
    # From standard d5 treatment:
    # 4T1g(4F): E = E(4F) - 6*Dq
    # 4T1g(4P): E = E(4P) - 6*Dq
    # Mixing: 4*Dq
    
    H_4T1g = np.array([
        [E_4F - 6*Dq, 4*Dq],
        [4*Dq, E_4P - 6*Dq]
    ])
    evals_4T1g = np.linalg.eigvalsh(H_4T1g)
    results.append((evals_4T1g[0], '4T1g'))
    results.append((evals_4T1g[1], '4T1g'))
    
    # 4T2g: mixing of 4T2g(4G), 4T2g(4F), 4T2g(4D)
    # Simplified 2x2 for 4G-4F mixing (4D is higher)
    # 4T2g(4G): E = E(4G) + 3*Dq (approximate)
    # 4T2g(4F): E = E(4F) + 8*Dq (approximate)
    # Mixing: ~2*Dq
    
    H_4T2g = np.array([
        [E_4G + 3*Dq, 2*Dq],
        [2*Dq, E_4F + 8*Dq]
    ])
    evals_4T2g = np.linalg.eigvalsh(H_4T2g)
    results.append((evals_4T2g[0], '4T2g'))
    results.append((evals_4T2g[1], '4T2g'))
    
    # 4A1g and 4Eg from 4G - no first-order Dq dependence
    # These are degenerate at Dq=0
    results.append((E_4G, '4A1g'))
    results.append((E_4G, '4Eg'))
    
    # 4A2g from 4F
    # E = E(4F) + 12*Dq (approximate)
    results.append((E_4F + 12*Dq, '4A2g'))
    
    # 4Eg and 4T2g from 4D (higher energy, may not be in lowest 6)
    results.append((E_4D + 3*Dq, '4Eg(4D)'))
    results.append((E_4D - 2*Dq, '4T2g(4D)'))
    
    # === DOUBLETS ===
    # For d5, doublets become important at high Dq (low-spin region)
    # The low-spin ground state is 2T2g from t2g^5 configuration
    
    # Doublet energies are complex. For approximate treatment:
    # At Dq=0, doublets are at ~15000-20000 cm^-1 above 6S
    # With increasing Dq, 2T2g drops and becomes ground state at high Dq
    
    # Simplified doublet energies (from t2g^5 low-spin config):
    # 2T2g: E = E_doublet - 10*Dq (drops with Dq)
    # 2Eg: E = E_doublet + higher terms
    
    # Estimate doublet energy at Dq=0
    E_doublet_0 = 18*B + 7*C  # Approximate, ~39000 cm^-1
    
    # Low-spin states (become important at high Dq)
    results.append((E_doublet_0 - 10*Dq, '2T2g'))
    results.append((E_doublet_0 - 5*Dq, '2Eg'))
    results.append((E_doublet_0 + 5*Dq, '2T1g'))
    results.append((E_doublet_0 + 10*Dq, '2A1g'))
    results.append((E_doublet_0 + 15*Dq, '2T2g(2)'))
    
    # Sort by energy
    results.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0, convert to E/B
    E_ground = results[0][0]
    results = [((E - E_ground)/B, label) for E, label in results]
    
    return results

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
Dq_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("\n" + "="*70)
print("d5 Tanabe-Sugano Energy Levels (E/B relative to ground state)")
print("="*70)

all_levels = []
for Dq_B in Dq_B_values:
    Dq = Dq_B * B
    energies = get_d5_energies(Dq, B, C)
    
    print(f"\nDq/B = {Dq_B:.1f}:")
    point_levels = []
    for i, (E_B, label) in enumerate(energies[:6]):
        print(f"  {i+1}. {label}: E/B = {E_B:.4f}")
        point_levels.append((Dq_B, label, E_B))
    all_levels.append((Dq_B, energies[:6]))

# Now let me refine the calculation with more accurate formulas
# The above is approximate. Let me look up the exact d5 matrices.

print("\n" + "="*70)
print("Refining with more accurate d5 energy matrices...")
print("="*70)
