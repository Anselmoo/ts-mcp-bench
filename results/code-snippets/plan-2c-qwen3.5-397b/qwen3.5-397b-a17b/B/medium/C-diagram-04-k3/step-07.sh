cat << 'EOF' > tanabe_sugano_numbered.py
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

B = 551.0
C = 2511.0
C_over_B = C / B

E_5D = 0.0
E_3P = 15.0 * B
E_3H = -9.0 * B + 5.0 * C
E_3F = 15.0 * B + 5.0 * C
E_3G = 12.0 * B + 5.0 * C
E_1I = 22.0 * B + 10.0 * C
E_1G = 12.0 * B + 7.0 * C
E_1D = 10.0 * B + 5.0 * C
E_1S = 22.0 * B + 14.0 * C

def compute_energies(Dq, B, C):
    energies = []
    
    # QUINTET
    energies.append(('5T2g', -4.0 * Dq))
    energies.append(('5Eg', 6.0 * Dq))
    
    # TRIPLET T1g (5 states)
    H = np.zeros((5, 5))
    H[0, 0] = E_3P
    H[1, 1] = E_3F - 2*Dq
    H[2, 2] = E_3G - 2*Dq
    H[3, 3] = E_3H
    H[4, 4] = E_3H + 5*B
    H[0, 1] = H[1, 0] = 4*Dq/np.sqrt(6)
    H[1, 2] = H[2, 1] = 2*Dq
    H[2, 3] = H[3, 2] = Dq
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'3T1g({i+1})', E))
    
    # TRIPLET T2g (3 states)
    H = np.zeros((3, 3))
    H[0, 0] = E_3F + 4*Dq
    H[1, 1] = E_3G - 4*Dq
    H[2, 2] = E_3H + 2*B
    H[0, 1] = H[1, 0] = 2*Dq
    H[1, 2] = H[2, 1] = Dq
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'3T2g({i+1})', E))
    
    # TRIPLET Eg (2 states)
    H = np.zeros((2, 2))
    H[0, 0] = E_3H + B
    H[1, 1] = E_3G + 2*Dq
    H[0, 1] = H[1, 0] = Dq
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'3Eg({i+1})', E))
    
    # TRIPLET A2g, A1g
    energies.append(('3A2g', E_3F - 6*Dq))
    energies.append(('3A1g', E_3G + 4*Dq))
    
    # SINGLET A1g (3 states)
    H = np.zeros((3, 3))
    H[0, 0] = 15*B + 5*C - 24*Dq
    H[1, 1] = E_1G + 4*Dq
    H[2, 2] = E_1S
    H[0, 1] = H[1, 0] = 2*B
    H[1, 2] = H[2, 1] = 2*B
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'1A1g({i+1})', E))
    
    # SINGLET T1g (2 states)
    H = np.zeros((2, 2))
    H[0, 0] = E_1G - 2*Dq
    H[1, 1] = E_1I + Dq
    H[0, 1] = H[1, 0] = B
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'1T1g({i+1})', E))
    
    # SINGLET T2g (3 states)
    H = np.zeros((3, 3))
    H[0, 0] = E_1D + 6*Dq
    H[1, 1] = E_1G - 4*Dq
    H[2, 2] = E_1I - Dq
    H[0, 1] = H[1, 0] = B
    H[1, 2] = H[2, 1] = B
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'1T2g({i+1})', E))
    
    # SINGLET Eg (3 states)
    H = np.zeros((3, 3))
    H[0, 0] = E_1D - 4*Dq
    H[1, 1] = E_1G + 2*Dq
    H[2, 2] = E_1I + 3*Dq
    H[0, 1] = H[1, 0] = B
    H[1, 2] = H[2, 1] = B
    for i, E in enumerate(sorted(np.linalg.eigvalsh(H))):
        energies.append((f'1Eg({i+1})', E))
    
    # SINGLET A2g
    energies.append(('1A2g', E_1I + 5*Dq))
    
    energies.sort(key=lambda x: x[1])
    return energies

dq_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
results = []

for dq_b in dq_b_values:
    Dq = dq_b * B
    energies = compute_energies(Dq, B, C)
    E_ground = energies[0][1]
    relative = [(label, (E - E_ground) / B) for label, E in energies]
    lowest_6 = relative[:6]
    results.append((dq_b, lowest_6))

# Plot
dq_b_fine = np.linspace(0, 4, 400)
curves = {}
for dq_b in dq_b_fine:
    Dq = dq_b * B
    energies = compute_energies(Dq, B, C)
    E_ground = energies[0][1]
    for label, E in energies:
        e_rel = (E - E_ground) / B
        base = label.split('(')[0]
        key = f"{base}"
        if key not in curves:
            curves[key] = {'dq': [], 'e': []}
        curves[key]['dq'].append(dq_b)
        curves[key]['e'].append(e_rel)

fig, ax = plt.subplots(figsize=(14, 10))
for label, data in curves.items():
    if label.startswith('5'):
        color, lw = 'blue', 2.5
    elif label.startswith('3'):
        color, lw = 'red', 1.5
    else:
        color, lw = 'green', 1.0
    ax.plot(data['dq'], data['e'], color=color, linewidth=lw, alpha=0.7, label=label)

ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁶ Octahedral Ion\n(B = 551 cm⁻¹, C = 2511 cm⁻¹)', fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(0, 4)
ax.set_ylim(-2, 50)
ax.legend(loc='upper right', fontsize=8, ncol=3)
plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("Results:")
for dq_b, lowest_6 in results:
    print(f"Dq/B = {dq_b}:")
    for label, e_rel in lowest_6:
        print(f"  {label}: E/B = {e_rel:.4f}")
    print()
EOF
python3 tanabe_sugano_numbered.py