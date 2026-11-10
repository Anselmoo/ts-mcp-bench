import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Tanabe-Sugano diagram for d^6 octahedral ion
# Properly labeling states by their parent free-ion terms

B = 551.0  # cm^-1
C = 2511.0  # cm^-1
C_over_B = C / B

print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.3f}")
print()

# Free ion term energies for d^6 (relative to 5D = 0)
E_5D = 0.0
E_3P = 15.0 * B
E_3H = -9.0 * B + 5.0 * C
E_3F = 15.0 * B + 5.0 * C
E_3G = 12.0 * B + 5.0 * C
E_1I = 22.0 * B + 10.0 * C
E_1G = 12.0 * B + 7.0 * C
E_1D = 10.0 * B + 5.0 * C
E_1S = 22.0 * B + 14.0 * C

def compute_energies_labeled(Dq, B, C):
    """
    Compute energy levels for d^6 with proper parent term labels.
    Returns list of (label, E) sorted by energy.
    """
    energies = []
    
    # ============== QUINTET STATES (from 5D) ==============
    energies.append(('5T2g', -4.0 * Dq))
    energies.append(('5Eg', 6.0 * Dq))
    
    # ============== TRIPLET STATES ==============
    
    # 3T1g states: from 3P, 3F, 3G, 3H (two from H)
    # Build 5x5 matrix for all 3T1g states
    H_3T1g = np.zeros((5, 5))
    
    # Diagonal elements
    H_3T1g[0, 0] = E_3P  # from 3P
    H_3T1g[1, 1] = E_3F - 2*Dq  # from 3F
    H_3T1g[2, 2] = E_3G - 2*Dq  # from 3G
    H_3T1g[3, 3] = E_3H  # from 3H (first)
    H_3T1g[4, 4] = E_3H + 5*B  # from 3H (second, slightly higher)
    
    # Off-diagonal mixing (approximate)
    H_3T1g[0, 1] = H_3T1g[1, 0] = 4*Dq/np.sqrt(6)
    H_3T1g[1, 2] = H_3T1g[2, 1] = 2*Dq
    H_3T1g[2, 3] = H_3T1g[3, 2] = Dq
    
    evals_3T1g = np.linalg.eigvalsh(H_3T1g)
    labels_3T1g = ['3T1g(P)', '3T1g(F)', '3T1g(G)', '3T1g(H)', '3T1g(H)']
    sorted_indices = np.argsort(evals_3T1g)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_3T1g[idx], evals_3T1g[idx]))
    
    # 3T2g states: from 3F, 3G, 3H
    H_3T2g = np.zeros((3, 3))
    H_3T2g[0, 0] = E_3F + 4*Dq  # from 3F
    H_3T2g[1, 1] = E_3G - 4*Dq  # from 3G
    H_3T2g[2, 2] = E_3H + 2*B  # from 3H
    
    H_3T2g[0, 1] = H_3T2g[1, 0] = 2*Dq
    H_3T2g[1, 2] = H_3T2g[2, 1] = Dq
    
    evals_3T2g = np.linalg.eigvalsh(H_3T2g)
    labels_3T2g = ['3T2g(F)', '3T2g(G)', '3T2g(H)']
    sorted_indices = np.argsort(evals_3T2g)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_3T2g[idx], evals_3T2g[idx]))
    
    # 3Eg states: from 3H, 3G
    H_3Eg = np.zeros((2, 2))
    H_3Eg[0, 0] = E_3H + B  # from 3H
    H_3Eg[1, 1] = E_3G + 2*Dq  # from 3G
    H_3Eg[0, 1] = H_3Eg[1, 0] = Dq
    
    evals_3Eg = np.linalg.eigvalsh(H_3Eg)
    labels_3Eg = ['3Eg(H)', '3Eg(G)']
    sorted_indices = np.argsort(evals_3Eg)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_3Eg[idx], evals_3Eg[idx]))
    
    # 3A2g from 3F
    energies.append(('3A2g(F)', E_3F - 6*Dq))
    
    # 3A1g from 3G
    energies.append(('3A1g(G)', E_3G + 4*Dq))
    
    # ============== SINGLET STATES ==============
    
    # 1A1g states: from 1I (low-spin), 1G, 1S
    H_1A1g = np.zeros((3, 3))
    H_1A1g[0, 0] = 15*B + 5*C - 24*Dq  # from 1I (low-spin ground at high Dq)
    H_1A1g[1, 1] = E_1G + 4*Dq  # from 1G
    H_1A1g[2, 2] = E_1S  # from 1S
    
    H_1A1g[0, 1] = H_1A1g[1, 0] = 2*B
    H_1A1g[1, 2] = H_1A1g[2, 1] = 2*B
    
    evals_1A1g = np.linalg.eigvalsh(H_1A1g)
    labels_1A1g = ['1A1g(I)', '1A1g(G)', '1A1g(S)']
    sorted_indices = np.argsort(evals_1A1g)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_1A1g[idx], evals_1A1g[idx]))
    
    # 1T1g states: from 1G, 1I
    H_1T1g = np.zeros((2, 2))
    H_1T1g[0, 0] = E_1G - 2*Dq
    H_1T1g[1, 1] = E_1I + Dq
    H_1T1g[0, 1] = H_1T1g[1, 0] = B
    
    evals_1T1g = np.linalg.eigvalsh(H_1T1g)
    labels_1T1g = ['1T1g(G)', '1T1g(I)']
    sorted_indices = np.argsort(evals_1T1g)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_1T1g[idx], evals_1T1g[idx]))
    
    # 1T2g states: from 1D, 1G, 1I
    H_1T2g = np.zeros((3, 3))
    H_1T2g[0, 0] = E_1D + 6*Dq
    H_1T2g[1, 1] = E_1G - 4*Dq
    H_1T2g[2, 2] = E_1I - Dq
    H_1T2g[0, 1] = H_1T2g[1, 0] = B
    H_1T2g[1, 2] = H_1T2g[2, 1] = B
    
    evals_1T2g = np.linalg.eigvalsh(H_1T2g)
    labels_1T2g = ['1T2g(D)', '1T2g(G)', '1T2g(I)']
    sorted_indices = np.argsort(evals_1T2g)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_1T2g[idx], evals_1T2g[idx]))
    
    # 1Eg states: from 1D, 1G, 1I
    H_1Eg = np.zeros((3, 3))
    H_1Eg[0, 0] = E_1D - 4*Dq
    H_1Eg[1, 1] = E_1G + 2*Dq
    H_1Eg[2, 2] = E_1I + 3*Dq
    H_1Eg[0, 1] = H_1Eg[1, 0] = B
    H_1Eg[1, 2] = H_1Eg[2, 1] = B
    
    evals_1Eg = np.linalg.eigvalsh(H_1Eg)
    labels_1Eg = ['1Eg(D)', '1Eg(G)', '1Eg(I)']
    sorted_indices = np.argsort(evals_1Eg)
    for i, idx in enumerate(sorted_indices):
        energies.append((labels_1Eg[idx], evals_1Eg[idx]))
    
    # 1A2g from 1I
    energies.append(('1A2g(I)', E_1I + 5*Dq))
    
    # Sort by energy
    energies.sort(key=lambda x: x[1])
    
    return energies

# Compute for Dq/B = 0, 0.5, 1.0, ..., 4.0
dq_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

for dq_b in dq_b_values:
    Dq = dq_b * B
    energies = compute_energies_labeled(Dq, B, C)
    
    # Convert to E/B relative to ground state
    E_ground = energies[0][1]
    relative = [(label, (E - E_ground) / B) for label, E in energies]
    
    # Take lowest 6
    lowest_6 = relative[:6]
    results.append((dq_b, lowest_6))
    
    print(f"Dq/B = {dq_b}:")
    for label, e_rel in lowest_6:
        print(f"  {label}: E/B = {e_rel:.4f}")
    print()

# Generate plot
print("Generating plot...")

dq_b_fine = np.linspace(0, 4, 400)
curves = {}

for dq_b in dq_b_fine:
    Dq = dq_b * B
    energies = compute_energies_labeled(Dq, B, C)
    E_ground = energies[0][1]
    
    for i, (label, E) in enumerate(energies):
        e_rel = (E - E_ground) / B
        # Simplify label for plotting (remove parent in parentheses for clarity)
        simple_label = label.split('(')[0]
        key = f"{simple_label}_{i}"
        if key not in curves:
            curves[key] = {'dq': [], 'e': [], 'label': simple_label}
        curves[key]['dq'].append(dq_b)
        curves[key]['e'].append(e_rel)

fig, ax = plt.subplots(figsize=(14, 10))

for key, data in curves.items():
    label = data['label']
    if label.startswith('5'):
        color = 'blue'
        linewidth = 2.5
    elif label.startswith('3'):
        color = 'red'
        linewidth = 1.5
    else:
        color = 'green'
        linewidth = 1.0
    
    ax.plot(data['dq'], data['e'], color=color, linewidth=linewidth, alpha=0.7)

ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁶ Octahedral Ion\n(B = 551 cm⁻¹, C = 2511 cm⁻¹)', 
             fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 4)
ax.set_ylim(-2, 50)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("Plot saved as diagram.png")

# Print final results
print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
for dq_b, lowest_6 in results:
    print(f"Dq/B = {dq_b}:")
    for label, e_rel in lowest_6:
        print(f"  {label}: E/B = {e_rel:.4f}")
    print()
