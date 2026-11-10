"""
Final structured output for d5 Tanabe-Sugano diagram.
"""

import json
import hashlib

# Racah parameters
B = 806.0  # cm^-1
C = 3570.0  # cm^-1

def solve_d5_energies(Dq, B, C):
    """Compute all energy levels for d5 in octahedral field."""
    
    # Free ion term energies relative to 6S ground state
    E_4G = 10*B + 5*C
    E_4P = 15*B + 5*C
    E_4F = 7*B + 5*C
    E_4D = 12*B + 5*C
    E_doublet_base = 18*B + 6*C
    
    import numpy as np
    results = []
    
    # Sextet
    results.append((0.0, '6A1g'))
    
    # 4T1g: 2x2 matrix
    H_4T1g = np.array([
        [E_4F - 6*Dq, 4*Dq],
        [4*Dq, E_4P - 6*Dq]
    ])
    evals_4T1g = np.linalg.eigvalsh(H_4T1g)
    results.append((evals_4T1g[0], '4T1g'))
    results.append((evals_4T1g[1], '4T1g'))
    
    # 4T2g: 3x3 matrix
    H_4T2g = np.array([
        [E_4G + 3*Dq, 2*Dq, 0],
        [2*Dq, E_4F + 8*Dq, Dq],
        [0, Dq, E_4D - 2*Dq]
    ])
    evals_4T2g = np.linalg.eigvalsh(H_4T2g)
    results.append((evals_4T2g[0], '4T2g'))
    results.append((evals_4T2g[1], '4T2g'))
    results.append((evals_4T2g[2], '4T2g'))
    
    # 4A1g and 4Eg from 4G
    results.append((E_4G, '4A1g'))
    results.append((E_4G, '4Eg'))
    
    # 4A2g from 4F
    results.append((E_4F + 12*Dq, '4A2g'))
    
    # 4Eg from 4D
    results.append((E_4D + 3*Dq, '4Eg'))
    
    # Doublets
    pairing = 2*B
    results.append((E_doublet_base - 20*Dq + pairing, '2T2g'))
    results.append((E_doublet_base - 14*Dq + pairing, '2Eg'))
    results.append((E_doublet_base - 10*Dq + pairing, '2T1g'))
    results.append((E_doublet_base - 6*Dq + pairing, '2A2g'))
    results.append((E_doublet_base - 2*Dq + pairing, '2T2g'))
    results.append((E_doublet_base + 2*Dq + pairing, '2A1g'))
    
    # Sort and normalize
    results.sort(key=lambda x: x[0])
    E_ground = results[0][0]
    results_EB = [((E - E_ground)/B, label) for E, label in results]
    
    return results_EB

# Compute for all Dq/B values
Dq_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

points = []
for Dq_B in Dq_B_values:
    Dq = Dq_B * B
    energies = solve_d5_energies(Dq, B, C)
    
    levels = []
    for E_B, label in energies[:6]:
        levels.append({'term': label, 'e_over_b': round(E_B, 4)})
    
    points.append({'dq_over_b': Dq_B, 'levels': levels})

# Get image info
image_path = 'diagram.png'
with open(image_path, 'rb') as f:
    image_sha256 = hashlib.sha256(f.read()).hexdigest()

# Create structured output
output = {
    'points': points,
    'image_path': image_path,
    'image_sha256': image_sha256,
    'reason': 'Tanabe-Sugano diagram for d⁵ octahedral ion showing high-spin 6A1g ground state at low Dq/B transitioning to low-spin 2T2g ground state at high Dq/B.'
}

print(json.dumps(output, indent=2))
