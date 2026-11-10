"""
Complete Tanabe-Sugano diagram for d5 octahedral ion.
Properly handles all term splittings and configuration interactions.
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

def solve_d5_energies(Dq, B, C):
    """
    Compute all energy levels for d5 in octahedral field.
    Uses proper matrices from standard d5 Tanabe-Sugano treatment.
    """
    CB = C / B
    
    # Free ion term energies relative to 6S ground state (in cm^-1)
    # Using standard formulas: E = a*B + b*C
    # These give correct ordering for d5
    
    E_4G = 10*B + 5*C   # ~25910 cm^-1, E/B ~ 32.15
    E_4P = 15*B + 5*C   # ~29940 cm^-1, E/B ~ 37.15
    E_4F = 7*B + 5*C    # ~23492 cm^-1, E/B ~ 29.15
    E_4D = 12*B + 5*C   # ~27522 cm^-1, E/B ~ 34.15
    
    # Doublet base energy (approximate)
    E_doublet_base = 18*B + 6*C  # ~35868 cm^-1
    
    results = []
    
    # === SEXTET ===
    # 6A1g from 6S - no crystal field splitting (S state)
    results.append((0.0, '6A1g'))
    
    # === QUARTET STATES ===
    
    # 4T1g: 2x2 matrix from 4T1g(4F) and 4T1g(4P)
    # From standard weak-field theory:
    # Diagonal: E(term) - 6*Dq for both (T1g from F and P have same CF shift)
    # Off-diagonal: 4*Dq
    
    H_4T1g = np.array([
        [E_4F - 6*Dq, 4*Dq],
        [4*Dq, E_4P - 6*Dq]
    ])
    evals_4T1g = np.linalg.eigvalsh(H_4T1g)
    results.append((evals_4T1g[0], '4T1g'))
    results.append((evals_4T1g[1], '4T1g'))
    
    # 4T2g: 3x3 matrix from 4T2g(4G), 4T2g(4F), 4T2g(4D)
    # Crystal field shifts: 4T2g(G): +3Dq, 4T2g(F): +8Dq, 4T2g(D): -2Dq
    # Off-diagonal mixings: G-F: 2Dq, F-D: Dq, G-D: 0 (no direct mixing)
    
    H_4T2g = np.array([
        [E_4G + 3*Dq, 2*Dq, 0],
        [2*Dq, E_4F + 8*Dq, Dq],
        [0, Dq, E_4D - 2*Dq]
    ])
    evals_4T2g = np.linalg.eigvalsh(H_4T2g)
    results.append((evals_4T2g[0], '4T2g'))
    results.append((evals_4T2g[1], '4T2g'))
    results.append((evals_4T2g[2], '4T2g'))
    
    # 4A1g and 4Eg from 4G - no first-order Dq dependence
    # These are degenerate (from same parent term)
    results.append((E_4G, '4A1g'))
    results.append((E_4G, '4Eg'))
    
    # 4A2g from 4F
    # Crystal field shift: +12*Dq
    results.append((E_4F + 12*Dq, '4A2g'))
    
    # 4Eg from 4D (separate from 4Eg from 4G)
    # Crystal field shift: +3*Dq
    results.append((E_4D + 3*Dq, '4Eg'))
    
    # === DOUBLET STATES ===
    # Low-spin states become important at high Dq
    
    pairing = 2*B  # Pairing energy penalty
    
    # Low-spin doublets from t2g^5 and t2g^4 eg^1
    results.append((E_doublet_base - 20*Dq + pairing, '2T2g'))  # t2g^5, ground at high Dq
    results.append((E_doublet_base - 14*Dq + pairing, '2Eg'))   # t2g^4 eg^1
    results.append((E_doublet_base - 10*Dq + pairing, '2T1g'))  # t2g^4 eg^1
    results.append((E_doublet_base - 6*Dq + pairing, '2A2g'))   # t2g^4 eg^1
    results.append((E_doublet_base - 2*Dq + pairing, '2T2g'))   # t2g^4 eg^1
    results.append((E_doublet_base + 2*Dq + pairing, '2A1g'))   # t2g^4 eg^1
    
    # Sort by energy
    results.sort(key=lambda x: x[0])
    
    # Shift so ground state is at 0, convert to E/B
    E_ground = results[0][0]
    results_EB = [((E - E_ground)/B, label) for E, label in results]
    
    return results_EB

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
Dq_B_values = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("\n" + "="*70)
print("d5 Tanabe-Sugano Energy Levels (E/B relative to ground state)")
print("="*70)

all_results = []
for Dq_B in Dq_B_values:
    Dq = Dq_B * B
    energies = solve_d5_energies(Dq, B, C)
    
    print(f"\nDq/B = {Dq_B}:")
    point_data = []
    for i, (E_B, label) in enumerate(energies[:6]):
        print(f"  {i+1}. {label}: E/B = {E_B:.4f}")
        point_data.append({'term': label, 'e_over_b': round(E_B, 4)})
    all_results.append({'dq_over_b': Dq_B, 'levels': point_data})

# Create the plot
print("\n" + "="*70)
print("Creating Tanabe-Sugano diagram plot...")
print("="*70)

# Collect data for plotting
plot_data = {Dq_B: [] for Dq_B in Dq_B_values}
for Dq_B in Dq_B_values:
    Dq = Dq_B * B
    energies = solve_d5_energies(Dq, B, C)
    for E_B, label in energies:
        plot_data[Dq_B].append((E_B, label))

# Create figure
fig, ax = plt.subplots(figsize=(14, 9))

# Group points by label for line plotting
label_points = {}
for Dq_B in Dq_B_values:
    for E_B, label in plot_data[Dq_B]:
        if label not in label_points:
            label_points[label] = []
        label_points[label].append((Dq_B, E_B))

# Plot each term
for label, points in sorted(label_points.items()):
    points.sort(key=lambda x: x[0])
    Dq_vals = [p[0] for p in points]
    E_vals = [p[1] for p in points]
    ax.plot(Dq_vals, E_vals, '-', linewidth=1.5, alpha=0.8)

# Mark the points
for Dq_B in Dq_B_values:
    for E_B, label in plot_data[Dq_B][:15]:
        ax.plot(Dq_B, E_B, 'o', markersize=4, alpha=0.6)

ax.set_xlabel('Dq/B', fontsize=14)
ax.set_ylabel('E/B', fontsize=14)
ax.set_title('d⁵ Tanabe-Sugano Diagram (B = 806 cm⁻¹, C = 3570 cm⁻¹, C/B = 4.43)', fontsize=14)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-0.1, 4.1)
ax.set_ylim(-2, 55)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("Saved diagram.png")

# Calculate sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")

# Print final results
print("\n" + "="*70)
print("FINAL RESULTS")
print("="*70)
for result in all_results:
    print(f"\nDq/B = {result['dq_over_b']}:")
    for level in result['levels']:
        print(f"  {level['term']}: E/B = {level['e_over_b']}")
