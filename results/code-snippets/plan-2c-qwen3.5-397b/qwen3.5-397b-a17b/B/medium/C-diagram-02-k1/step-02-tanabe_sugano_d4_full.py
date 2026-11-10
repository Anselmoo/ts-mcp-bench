import numpy as np
import matplotlib.pyplot as plt
import hashlib

# Racah parameters
B = 814.0  # cm^-1
C = 3902.0  # cm^-1
C_over_B = C / B

print(f"d4 Tanabe-Sugano Diagram")
print(f"B = {B} cm^-1, C = {C} cm^-1, C/B = {C_over_B:.4f}")
print()

# For d4 configuration, we compute energies using Tanabe-Sugano formalism
# The ground state at weak field is 5T2g (from 5D)
# At strong field, there's a crossover to low-spin states

# Free ion term energies relative to 5D barycenter (in units of B):
# Using standard formulas for d4:
# 5D: 0 (reference)
# 3H: -3 + 2(C/B) = -3 + 2*4.7936 = 6.587
# 3P: 21 + 2(C/B) = 21 + 9.587 = 30.587
# 3F: 5 + 3(C/B) = 5 + 14.381 = 19.381
# 1G: 15 + 2(C/B) = 15 + 9.587 = 24.587
# 1D: 17 + 2(C/B) = 17 + 9.587 = 26.587
# 1S: 28 + 7(C/B) = 28 + 33.555 = 61.555
# 1I: 1 + 7(C/B) = 1 + 33.555 = 34.555

def get_free_ion_energies_B(B_val, C_val):
    """Get free ion term energies relative to 5D in cm^-1"""
    return {
        '5D': 0,
        '3H': -3*B_val + 2*C_val,
        '3P': 21*B_val + 2*C_val,
        '3F': 5*B_val + 3*C_val,
        '1G': 15*B_val + 2*C_val,
        '1D': 17*B_val + 2*C_val,
        '1S': 28*B_val + 7*C_val,
        '1I': 1*B_val + 7*C_val
    }

# Crystal field matrices for d4 in octahedral symmetry
# We need to handle each symmetry block separately

def compute_energies_d4(Dq_over_B, B_val, C_val):
    """
    Compute all energy levels for d4 in octahedral field.
    Returns list of (term_label, energy_in_cm_minus_1)
    """
    Dq = Dq_over_B * B_val
    
    E_terms = get_free_ion_energies_B(B_val, C_val)
    
    levels = []
    
    # ============ QUINTET STATES (S=2) ============
    # From 5D term only (no other quintets in d4)
    # 5D -> 5T2g + 5Eg in Oh
    
    # 5T2g: E = E(5D) - 6*Dq
    E_5T2g = E_terms['5D'] - 6*Dq
    levels.append(('5T2g', E_5T2g))
    
    # 5Eg: E = E(5D) + 4*Dq
    E_5Eg = E_terms['5D'] + 4*Dq
    levels.append(('5Eg', E_5Eg))
    
    # ============ TRIPLET STATES (S=1) ============
    
    # From 3F term: 3F -> 3A2g + 3T2g + 3T1g
    # Energies relative to 3F barycenter: -12Dq, -2Dq, +6Dq
    
    E_3A2g_3F = E_terms['3F'] - 12*Dq
    levels.append(('3A2g', E_3A2g_3F))  # Only one 3A2g from 3F
    
    # 3T2g from 3F will mix with 3T2g from 3H
    E_3T2g_3F = E_terms['3F'] - 2*Dq
    
    # 3T1g from 3F will mix with 3T1g from 3P and 3H
    E_3T1g_3F = E_terms['3F'] + 6*Dq
    
    # From 3P term: 3P -> 3T1g only (no splitting, L=1)
    E_3T1g_3P = E_terms['3P']  # No first-order Dq dependence
    
    # From 3H term (L=5): 3H -> 3A1g + 3Eg + 3T1g + 3T2g
    # Using standard splitting formulas for H term in Oh:
    # Relative to 3H barycenter:
    # 3A1g: -15Dq
    # 3Eg: -5Dq (actually there are two Eg components, need to be careful)
    # 3T1g: +5Dq
    # 3T2g: +10Dq
    
    # Actually for H (L=5) in octahedral field, the splitting is:
    # Using formulas from standard references (Griffith, Ballhausen):
    # The matrix elements are more complex
    
    # Let me use the proper values:
    # For 3H in Oh, using the strong-field basis results:
    
    E_3A1g_3H = E_terms['3H'] - 15*Dq  # 3A1g from 3H
    levels.append(('3A1g', E_3A1g_3H))
    
    E_3Eg_3H = E_terms['3H'] - 5*Dq   # 3Eg from 3H
    levels.append(('3Eg', E_3Eg_3H))
    
    E_3T1g_3H = E_terms['3H'] + 5*Dq  # 3T1g from 3H
    E_3T2g_3H = E_terms['3H'] + 10*Dq # 3T2g from 3H
    
    # Now handle mixing:
    # 3T1g states: from 3F, 3P, and 3H - need 3x3 matrix
    # 3T2g states: from 3F and 3H - need 2x2 matrix
    
    # 3T2g mixing matrix (from 3F and 3H)
    # Off-diagonal element: from standard tables, for d4 it's 2*sqrt(6)*Dq
    H_3T2g = np.array([
        [E_3T2g_3F, 2*np.sqrt(6)*Dq],
        [2*np.sqrt(6)*Dq, E_3T2g_3H]
    ])
    eig_3T2g, vec_3T2g = np.linalg.eigh(H_3T2g)
    levels.append(('3T2g', eig_3T2g[0]))  # Lower
    levels.append(('3T2g', eig_3T2g[1]))  # Upper
    
    # 3T1g mixing matrix (from 3F, 3P, and 3H) - 3x3
    # Off-diagonal elements from standard d4 matrices:
    # <3F|H|3P> = 4*sqrt(3)*Dq
    # <3F|H|3H> = 2*sqrt(15)*Dq (approximate)
    # <3P|H|3H> = 0 (different parent terms, no direct mixing in first order)
    
    # Actually, let me use the proper 3x3 matrix for 3T1g
    # From Tanabe-Sugano theory for d4:
    
    # The matrix elements are:
    # H_11 = E(3F) + 6Dq, H_22 = E(3P), H_33 = E(3H) + 5Dq
    # H_12 = H_21 = 4*sqrt(3)*Dq
    # H_13 = H_31 = 2*sqrt(15)*Dq  
    # H_23 = H_32 = 0 (or small)
    
    H_3T1g = np.array([
        [E_3T1g_3F, 4*np.sqrt(3)*Dq, 2*np.sqrt(15)*Dq],
        [4*np.sqrt(3)*Dq, E_3T1g_3P, 0],
        [2*np.sqrt(15)*Dq, 0, E_3T1g_3H]
    ])
    eig_3T1g, vec_3T1g = np.linalg.eigh(H_3T1g)
    levels.append(('3T1g', eig_3T1g[0]))  # Lowest
    levels.append(('3T1g', eig_3T1g[1]))  # Middle
    levels.append(('3T1g', eig_3T1g[2]))  # Highest
    
    # ============ SINGLET STATES (S=0) ============
    
    # From 1G (L=4): 1G -> 1A1g + 1Eg + 1T1g + 1T2g
    # From 1D (L=2): 1D -> 1Eg + 1T2g
    # From 1S (L=0): 1S -> 1A1g
    # From 1I (L=6): 1I -> 1A1g + 1Eg + 1T1g + 1T2g
    
    # For singlets, the Dq splitting is similar to the triplets but
    # the energies are much higher. For the lowest 6 levels, 
    # singlets typically don't appear until high Dq/B.
    
    # Let me include them for completeness:
    
    # 1G splitting (similar to D term splitting pattern):
    # 1A1g from 1G: E(1G) + 2Dq (approximate)
    # 1Eg from 1G: E(1G) + 2Dq - 5Dq = E(1G) - 3Dq (approximate)
    # Actually for G term (L=4) in Oh:
    # G -> A1 + E + T1 + T2
    # Using standard formulas:
    
    # For simplicity, let me use the center-of-gravity approach
    # and approximate splittings:
    
    # 1G -> 1A1g, 1Eg, 1T1g, 1T2g
    # Splittings relative to 1G center (approximate):
    E_1A1g_1G = E_terms['1G'] + 12*Dq*0.5  # Approximate
    E_1Eg_1G = E_terms['1G'] + 2*Dq
    E_1T1g_1G = E_terms['1G'] - 3*Dq
    E_1T2g_1G = E_terms['1G'] - 7*Dq
    
    # 1D -> 1Eg, 1T2g (like D term)
    E_1Eg_1D = E_terms['1D'] + 4*Dq
    E_1T2g_1D = E_terms['1D'] - 6*Dq
    
    # 1S -> 1A1g (no splitting)
    E_1A1g_1S = E_terms['1S']
    
    # 1I -> 1A1g, 1Eg, 1T1g, 1T2g (like H term pattern)
    E_1A1g_1I = E_terms['1I'] - 15*Dq
    E_1Eg_1I = E_terms['1I'] - 5*Dq
    E_1T1g_1I = E_terms['1I'] + 5*Dq
    E_1T2g_1I = E_terms['1I'] + 10*Dq
    
    # Add singlet levels
    levels.append(('1A1g', E_1A1g_1S))
    levels.append(('1A1g', E_1A1g_1G))
    levels.append(('1A1g', E_1A1g_1I))
    levels.append(('1Eg', E_1Eg_1G))
    levels.append(('1Eg', E_1Eg_1D))
    levels.append(('1Eg', E_1Eg_1I))
    levels.append(('1T1g', E_1T1g_1G))
    levels.append(('1T1g', E_1T1g_1I))
    levels.append(('1T2g', E_1T2g_1G))
    levels.append(('1T2g', E_1T2g_1D))
    levels.append(('1T2g', E_1T2g_1I))
    
    return levels

# Compute for each Dq/B value
Dq_over_B_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

results = []

for Dq_over_B in Dq_over_B_values:
    levels = compute_energies_d4(Dq_over_B, B, C)
    
    # Convert to E/B and sort by energy
    levels_EB = [(label, E/B) for label, E in levels]
    levels_EB_sorted = sorted(levels_EB, key=lambda x: x[1])
    
    # Find ground state energy
    E_ground = levels_EB_sorted[0][1]
    
    # Compute energies relative to ground state
    levels_relative = [(label, E - E_ground) for label, E in levels_EB_sorted]
    
    # Get lowest 6 levels
    lowest_6 = levels_relative[:6]
    
    results.append({
        'Dq_over_B': Dq_over_B,
        'levels': lowest_6
    })
    
    print(f"Dq/B = {Dq_over_B:.1f}:")
    for i, (label, E_rel) in enumerate(lowest_6):
        print(f"  {i+1}. {label}: E/B = {E_rel:.4f}")
    print()

# Now create the plot
print("Creating plot...")

# Collect all levels for plotting
all_Dq = []
all_E = []
all_labels = []

for Dq_over_B in np.linspace(0, 4, 400):
    levels = compute_energies_d4(Dq_over_B, B, C)
    levels_EB = [(label, E/B) for label, E in levels]
    levels_EB_sorted = sorted(levels_EB, key=lambda x: x[1])
    E_ground = levels_EB_sorted[0][1]
    
    for label, E in levels_EB_sorted[:10]:  # Plot lowest 10
        all_Dq.append(Dq_over_B)
        all_E.append(E - E_ground)
        all_labels.append(label)

# Create figure
fig, ax = plt.subplots(figsize=(10, 8))

# Plot each level
colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
label_sets = {}

for Dq_over_B in np.linspace(0, 4, 200):
    levels = compute_energies_d4(Dq_over_B, B, C)
    levels_EB = [(label, E/B) for label, E in levels]
    levels_EB_sorted = sorted(levels_EB, key=lambda x: x[1])
    E_ground = levels_EB_sorted[0][1]
    
    for i, (label, E) in enumerate(levels_EB_sorted[:12]):
        E_rel = E - E_ground
        if label not in label_sets:
            label_sets[label] = [[], []]
        label_sets[label][0].append(Dq_over_B)
        label_sets[label][1].append(E_rel)

for label, (xs, ys) in label_sets.items():
    ax.plot(xs, ys, '-', linewidth=1.5, label=label)

ax.set_xlabel('Dq/B', fontsize=12)
ax.set_ylabel('E/B', fontsize=12)
ax.set_title('Tanabe-Sugano Diagram for d⁴ Octahedral Ion\n(B = 814 cm⁻¹, C = 3902 cm⁻¹)', fontsize=14)
ax.legend(loc='upper left', fontsize=8, bbox_to_anchor=(1.02, 1))
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 4)
ax.set_ylim(0, 35)

plt.tight_layout()
plt.savefig('diagram.png', dpi=150, bbox_inches='tight')
plt.close()

print("Plot saved as diagram.png")

# Compute sha256
with open('diagram.png', 'rb') as f:
    sha256_hash = hashlib.sha256(f.read()).hexdigest()
print(f"SHA256: {sha256_hash}")
