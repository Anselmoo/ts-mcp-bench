import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import hashlib

# Racah parameters
B = 551.0  # cm^-1
C = 2511.0  # cm^-1
C_over_B = C / B  # 4.557168784

def d6_TS_energies(Dq_over_B, C_over_B=C_over_B):
    """
    Calculate d6 octahedral Tanabe-Sugano energies using proper weak-field basis.
    
    Free ion term energies relative to 5D ground (from Racah parameterization for d6):
    - 5D: 0 (ground)
    - 3H: 9B above 5D
    - 3F: 15B above 5D
    - 3P: 15B + 7C above 5D (mixes with 3T1g from 3F)
    - 3G: 12B + 5C above 5D
    - 1I: 17B + 5C above 5D
    - 1G: 12B + 5C above 5D
    - 1D: 10B + 5C above 5D
    - 1S: 22B + 7C above 5D
    - 1F: 15B + 7C above 5D
    """
    DqB = Dq_over_B
    
    levels = []
    
    # ============== QUINTET STATES (S=2) ==============
    # From 5D term: splits into 5T2g + 5Eg in Oh
    # Relative to 5D barycenter: 5T2g at -4Dq, 5Eg at +6Dq
    levels.append((-4 * DqB, "5T2g"))
    levels.append((6 * DqB, "5Eg"))
    
    # ============== TRIPLET STATES (S=1) ==============
    
    # From 3F term (at 15B above 5D):
    # Splits into: 3A2g + 3T2g + 3T1g
    E_3F = 15.0
    # In octahedral field, using standard weak-field energies:
    # 3T1g(F): -6Dq + 15B
    # 3T2g(F): -1Dq + 15B
    # 3A2g(F): +9Dq + 15B
    levels.append((E_3F - 6 * DqB, "3T1g(F)"))  # Will be replaced after mixing
    levels.append((E_3F - 1 * DqB, "3T2g(F)"))
    levels.append((E_3F + 9 * DqB, "3A2g(F)"))
    
    # From 3P term (at 15B + 7C above 5D):
    # Only gives 3T1g which mixes with 3T1g from 3F
    E_3P = 15.0 + 7.0 * C_over_B
    
    # Diagonalize 2x2 matrix for the two 3T1g states
    # Off-diagonal element is 4Dq for d6
    H_3T1g = np.array([
        [E_3F - 6 * DqB, 4 * DqB],
        [4 * DqB, E_3P]
    ])
    eig_3T1g = np.linalg.eigvalsh(H_3T1g)
    # Replace the unmixed 3T1g(F) with the eigenvalues
    levels = [l for l in levels if l[1] != "3T1g(F)"]
    levels.append((eig_3T1g[0], "3T1g(F)"))
    levels.append((eig_3T1g[1], "3T1g(P)"))
    
    # From 3H term (at 9B above 5D):
    # 3H (L=5) splits in Oh into 5 components: 3T1g + 3T2g + 3A2g + 3T1g + 3T2g
    E_3H = 9.0
    
    # Using standard L=5 splitting in octahedral field (from Griffith):
    # The five components have energies (relative to 3H barycenter):
    # -10Dq, -5Dq, +5Dq, +10Dq, +15Dq
    levels.append((E_3H - 10 * DqB, "3T1g(H)"))   # Lowest from 3H
    levels.append((E_3H - 5 * DqB, "3T2g(H)"))    # Second from 3H
    levels.append((E_3H + 5 * DqB, "3A2g(H)"))    # Middle from 3H
    levels.append((E_3H + 10 * DqB, "3T1g(H2)"))  # Fourth from 3H
    levels.append((E_3H + 15 * DqB, "3T2g(H2)"))  # Highest from 3H
    
    # From 3G term (at 12B + 5C above 5D):
    # 3G (L=4) splits into: 3A1g + 3Eg + 3T1g + 3T2g
    E_3G = 12.0 + 5.0 * C_over_B
    levels.append((E_3G - 4 * DqB, "3A1g(G)"))
    levels.append((E_3G + 1 * DqB, "3Eg(G)"))
    levels.append((E_3G + 6 * DqB, "3T1g(G)"))
    levels.append((E_3G + 11 * DqB, "3T2g(G)"))
    
    # ============== SINGLET STATES (S=0) ==============
    
    # From 1I term (L=6, at 17B + 5C above 5D):
    # 1I splits into: 1A1g + 1Eg + 1T1g + 1T2g + 1Eg + 1T2g (6 components)
    E_1I = 17.0 + 5.0 * C_over_B
    
    # Using standard L=6 splitting in octahedral field:
    # Energies relative to 1I barycenter: -24Dq, -14Dq, -9Dq, -4Dq, +11Dq, +16Dq
    levels.append((E_1I - 24 * DqB, "1A1g(I)"))   # Drops steeply, becomes ground at strong field
    levels.append((E_1I - 14 * DqB, "1T1g(I)"))
    levels.append((E_1I - 9 * DqB, "1T2g(I)"))
    levels.append((E_1I - 4 * DqB, "1Eg(I)"))
    levels.append((E_1I + 11 * DqB, "1Eg(I2)"))
    levels.append((E_1I + 16 * DqB, "1T2g(I2)"))
    
    # From 1G term (L=4, at 12B + 5C above 5D):
    # 1G splits into: 1A1g + 1Eg + 1T1g + 1T2g
    E_1G = 12.0 + 5.0 * C_over_B
    levels.append((E_1G - 4 * DqB, "1A1g(G)"))
    levels.append((E_1G + 1 * DqB, "1Eg(G)"))
    levels.append((E_1G + 6 * DqB, "1T1g(G)"))
    levels.append((E_1G + 11 * DqB, "1T2g(G)"))
    
    # From 1D term (L=2, at 10B + 5C above 5D):
    # 1D splits into: 1Eg + 1T2g
    E_1D = 10.0 + 5.0 * C_over_B
    levels.append((E_1D - 6 * DqB, "1Eg(D)"))
    levels.append((E_1D + 4 * DqB, "1T2g(D)"))
    
    # From 1S term (L=0, at 22B + 7C above 5D):
    # 1S gives only 1A1g with no Dq dependence
    E_1S = 22.0 + 7.0 * C_over_B
    levels.append((E_1S, "1A1g(S)"))
    
    # From 1F term (L=3, at 15B + 7C above 5D):
    # 1F splits into: 1A2g + 1T1g + 1T2g
    E_1F = 15.0 + 7.0 * C_over_B
    levels.append((E_1F - 6 * DqB, "1A2g(F)"))
    levels.append((E_1F + 2 * DqB, "1T1g(F)"))
    levels.append((E_1F + 8 * DqB, "1T2g(F)"))
    
    # Sort by energy
    levels.sort(key=lambda x: x[0])
    
    # Normalize so ground state is at 0
    if levels:
        E_ground = levels[0][0]
        levels = [(E - E_ground, label) for E, label in levels]
    
    return levels


# Calculate for each Dq/B value
Dq_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d⁶ Octahedral Ion")
print(f"B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_over_B:.4f}")
print("=" * 70)

all_results = []

for DqB in Dq_B_values:
    levels = d6_TS_energies(DqB)
    
    print(f"\nDq/B = {DqB:.1f}:")
    print("  #   Term            E/B")
    print("  --  --------------  --------")
    for i, (E, label) in enumerate(levels[:12]):
        print(f"  {i+1:2d}   {label:14s}  {E:8.4f}")
    
    # Store lowest 6 levels
    lowest_6 = [(label, round(E, 6)) for E, label in levels[:6]]
    all_results.append({
        'Dq_over_B': DqB,
        'levels': lowest_6
    })

# Save results to JSON
with open('d6_ts_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)

# Create the plot
fig, ax = plt.subplots(figsize=(12, 9))

# Plot energy levels vs Dq/B
DqB_fine = np.linspace(0, 4, 400)

# Collect all energy curves
all_curves = []
for level_idx in range(20):  # Plot lowest 20 levels
    energies = []
    labels = []
    for DqB in DqB_fine:
        levels = d6_TS_energies(DqB)
        if level_idx < len(levels):
            energies.append(levels[level_idx][0])
            labels.append(levels[level_idx][1])
        else:
            energies.append(np.nan)
    if any(not np.isnan(e) for e in energies):
        all_curves.append((energies, labels[0] if labels else f"Level {level_idx}"))

# Plot each curve
colors = plt.cm.tab10(np.linspace(0, 1, 10))
for i, (energies, label) in enumerate(all_curves[:15]):
    color = colors[i % 10]
    ax.plot(DqB_fine, energies, color=color, linewidth=1.5, alpha=0.8, label=label if i < 8 else "")

ax.set_xlabel('Dq/B', fontsize=14, fontweight='bold')
ax.set_ylabel('E/B', fontsize=14, fontweight='bold')
ax.set_title('Tanabe-Sugano Diagram for d⁶ Octahedral Ion\n(B = 551 cm⁻¹, C = 2511 cm⁻¹, C/B = 4.56)', 
             fontsize=16, fontweight='bold')
ax.set_xlim(0, 4)
ax.set_ylim(0, 55)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(loc='upper right', fontsize=9, framealpha=0.9)

# Add crossover point annotation
ax.axvline(x=2.0, color='gray', linestyle=':', alpha=0.5)
ax.text(2.0, 52, 'Spin crossover region', ha='center', fontsize=10, alpha=0.7)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
print("\n" + "=" * 70)
print("Plot saved to diagram.png")

# Calculate sha256 of the diagram
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")

# Print final formatted results
print("\n" + "=" * 70)
print("FINAL RESULTS - Lowest 6 levels at each Dq/B:")
print("=" * 70)
for res in all_results:
    print(f"\nDq/B = {res['Dq_over_B']}:")
    for label, E in res['levels']:
        print(f"  {label}: E/B = {E}")

# Output in structured format for the answer
print("\n" + "=" * 70)
print("STRUCTURED OUTPUT:")
print("=" * 70)
for res in all_results:
    print(f"\nDq/B = {res['Dq_over_B']}:")
    for label, E in res['levels']:
        print(f"  Term: {label}, E/B = {E}")
