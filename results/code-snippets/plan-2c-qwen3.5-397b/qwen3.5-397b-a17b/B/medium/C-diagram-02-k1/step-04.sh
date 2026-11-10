cat > tanabe_sugano_final.py << 'EOF'
import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Racah parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B

print(f"d⁴ Tanabe-Sugano Diagram")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_over_B:.4f}")
print()

# Free ion term energies relative to 5D barycenter (in cm^-1):
def get_free_ion_energies(B_val, C_val):
    return {
        '5D': 0,
        '3P': 21*B_val + 2*C_val,
        '3F': 5*B_val + 3*C_val,
        '1G': 15*B_val + 2*C_val,
        '1D': 17*B_val + 2*C_val,
        '1S': 28*B_val + 7*C_val
    }

def compute_energies_d4(Dq_over_B, B_val, C_val):
    """Compute energy levels for d4 in octahedral field."""
    Dq = Dq_over_B * B_val
    E_terms = get_free_ion_energies(B_val, C_val)
    
    levels = []
    
    # ============ QUINTET STATES (S=2) ============
    # From 5D: 5T2g and 5Eg
    
    E_5T2g = -6*Dq
    levels.append(('5T2g', E_5T2g))
    
    E_5Eg = +4*Dq
    levels.append(('5Eg', E_5Eg))
    
    # ============ TRIPLET STATES (S=1) ============
    
    E_3F = E_terms['3F']
    E_3P = E_terms['3P']
    
    # From 3F: 3A2g, 3T2g, 3T1g
    E_3A2g = E_3F - 12*Dq
    levels.append(('3A2g', E_3A2g))
    
    E_3T2g = E_3F - 2*Dq
    levels.append(('3T2g', E_3T2g))
    
    E_3T1g_3F = E_3F + 6*Dq
    
    # From 3P: 3T1g (mixes with 3T1g from 3F)
    E_3T1g_3P = E_3P
    
    # 3T1g mixing matrix (2x2)
    H_3T1g = np.array([
        [E_3T1g_3F, 4*np.sqrt(3)*Dq],
        [4*np.sqrt(3)*Dq, E_3T1g_3P]
    ])
    eig_3T1g = np.linalg.eigvalsh(H_3T1g)
    
    # Label the 3T1g states by their dominant character at low Dq
    # Lower one is primarily 3T1g(3F), upper is primarily 3T1g(3P)
    levels.append(('3T1g(3F)', eig_3T1g[0]))
    levels.append(('3T1g(3P)', eig_3T1g[1]))
    
    # ============ SINGLET STATES (S=0) ============
    
    E_1G = E_terms['1G']
    E_1D = E_terms['1D']
    E_1S = E_terms['1S']
    
    # 1A1g from 1S (no splitting)
    levels.append(('1A1g(1S)', E_1S))
    
    # 1G term splits into 1A1g, 1Eg, 1T1g, 1T2g
    # Using approximate Dq dependence (singlets are high energy)
    # For G term: A1(+2Dq), E(-Dq), T1(-Dq), T2(0) - approximate, CoG preserving
    levels.append(('1A1g(1G)', E_1G + 2*Dq))
    levels.append(('1Eg(1G)', E_1G - Dq))
    levels.append(('1T1g(1G)', E_1G - Dq))
    levels.append(('1T2g(1G)', E_1G))
    
    # 1D term splits into 1Eg, 1T2g (like D term: Eg at +4Dq, T2g at -6Dq)
    levels.append(('1Eg(1D)', E_1D + 4*Dq))
    levels.append(('1T2g(1D)', E_1D - 6*Dq))
    
    return levels

# Compute for each Dq/B value
Dq_over_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

print("Energy levels (E/B relative to ground state):")
print("=" * 70)

for Dq_over_B in Dq_over_B_values:
    levels = compute_energies_d4(Dq_over_B, B, C)
    
    # Convert to E/B and sort by energy
    levels_EB = [(label, E/B) for label, E in levels]
    levels_EB_sorted = sorted(levels_EB, key=lambda x: x[1])
    
    # Ground state energy
    E_ground = levels_EB_sorted[0][1]
    
    # Compute energies relative to ground state
    levels_relative = [(label, E - E_ground) for label, E in levels_EB_sorted]
    
    # Get lowest 6 levels
    lowest_6 = levels_relative[:6]
    
    results.append({
        'Dq_over_B': Dq_over_B,
        'levels': lowest_6
    })
    
    print(f"\nDq/B = {Dq_over_B:.1f}:")
    for i, (label, E_rel) in enumerate(lowest_6):
        print(f"  {i+1}. {label}: E/B = {E_rel:.4f}")

# Create the plot
print("\n" + "=" * 70)
print("Creating plot...")

# Collect data for plotting
label_data = {}

for Dq_over_B in np.linspace(0, 4, 300):
    levels = compute_energies_d4(Dq_over_B, B, C)
    levels_EB = [(label, E/B) for label, E in levels]
    levels_EB_sorted = sorted(levels_EB, key=lambda x: x[1])
    E_ground = levels_EB_sorted[0][1]
    
    for label, E in levels_EB_sorted[:12]:
        E_rel = E - E_ground
        if label not in label_data:
            label_data[label] = {'x': [], 'y': []}
        label_data[label]['x'].append(Dq_over_B)
        label_data[label]['y'].append(E_rel)

fig, ax = plt.subplots(figsize=(12, 9))

colors = plt.cm.tab10(np.linspace(0, 1, 12))
color_idx = 0

for label, data in sorted(label_data.items()):
    ax.plot(data['x'], data['y'], '-', linewidth=2, label=label, color=colors[color_idx % 12])
    color_idx += 1

ax.set_xlabel('Dq/B', fontsize=14)
ax.set_ylabel('E/B', fontsize=14)
ax.set_title('Tanabe-Sugano Diagram for d⁴ Octahedral Ion\n(B = 814 cm⁻¹, C = 3902 cm⁻¹)', fontsize=16)
ax.legend(loc='upper left', fontsize=9, bbox_to_anchor=(1.02, 1))
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 4)
ax.set_ylim(0, 45)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("Plot saved as diagram.png")

# Compute sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")

# Final formatted output
print("\n" + "=" * 70)
print("FINAL RESULTS - Lowest 6 levels at each Dq/B:")
print("=" * 70)

output_data = []
for r in results:
    dq = r['Dq_over_B']
    levels_list = []
    for label, e in r['levels']:
        levels_list.append({"term": label, "e_over_b": round(e, 4)})
    output_data.append({"dq_over_b": dq, "levels": levels_list})
    
print("\nStructured output:")
import json
print(json.dumps(output_data, indent=2))
EOF
python3 tanabe_sugano_final.py