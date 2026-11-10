cat > final_results.py << 'EOF'
import numpy as np

# Racah parameters
B = 551.0  # cm^-1
C = 2511.0  # cm^-1
C_over_B = C / B  # ≈ 4.557

def get_d6_energies(dq_over_b, C_over_B=C_over_B):
    """Compute energy levels for d6 octahedral configuration."""
    x = dq_over_b  # Dq/B
    
    # Quintet states (from 5D)
    e_5T2g = -4 * x
    e_5Eg = 6 * x
    
    # Free ion energies (relative to 5D ground)
    E_3H = 13 + 5 * C_over_B   # ≈ 35.79
    E_3G = 18 + 3 * C_over_B   # ≈ 31.67
    E_3F = 9 + 2 * C_over_B    # ≈ 18.11
    E_3P = 15 + 7 * C_over_B   # ≈ 46.90
    E_1I = 25 + 8 * C_over_B   # ≈ 61.46
    E_1G = 20 + 6 * C_over_B   # ≈ 47.34
    E_1S = 30 + 10 * C_over_B  # ≈ 75.57
    
    # 3T1g from 3F and 3P mix (2x2 matrix)
    H_3T1g_FP = np.array([
        [E_3F - 6*x, 4*x],
        [4*x, E_3P]
    ])
    eig_3T1g_FP = np.linalg.eigvalsh(H_3T1g_FP)
    eig_3T1g_FP.sort()
    
    # Other triplet states
    e_3T1g_H = E_3H - 6*x
    e_3T1g_G = E_3G - 6*x
    e_3T2g_F = E_3F + 2*x
    e_3T2g_H = E_3H + 2*x
    e_3T2g_G = E_3G - 8*x
    e_3A1g_G = E_3G + 12*x
    e_3A2g_F = E_3F + 12*x
    e_3A2g_H = E_3H + 12*x
    e_3Eg_H1 = E_3H - 4*x
    e_3Eg_H2 = E_3H - 8*x
    e_3Eg_G1 = E_3G + 2*x
    e_3Eg_G2 = E_3G - 8*x  # Same as 3T2g(G) - this is a known degeneracy
    
    # Singlet states
    e_1A1g_I = E_1I - 24*x  # Low-spin ground state
    e_1A1g_G = E_1G + 12*x
    e_1A1g_S = E_1S
    e_1Eg_G = E_1G - 8*x
    e_1Eg_I1 = E_1I - 4*x
    e_1Eg_I2 = E_1I - 8*x
    e_1T1g_G = E_1G - 6*x
    e_1T1g_I = E_1I - 6*x
    e_1T2g_G = E_1G - 8*x
    e_1T2g_I1 = E_1I + 2*x
    e_1T2g_I2 = E_1I + 10*x
    
    # Collect all levels with unique labels
    all_levels = [
        ('5T2g', e_5T2g),
        ('5Eg', e_5Eg),
        ('3T1g', eig_3T1g_FP[0]),
        ('3T1g*', eig_3T1g_FP[1]),
        ('3T1g(H)', e_3T1g_H),
        ('3T1g(G)', e_3T1g_G),
        ('3T2g(F)', e_3T2g_F),
        ('3T2g(H)', e_3T2g_H),
        ('3T2g(G)', e_3T2g_G),
        ('3A1g(G)', e_3A1g_G),
        ('3A2g(F)', e_3A2g_F),
        ('3A2g(H)', e_3A2g_H),
        ('3Eg(H1)', e_3Eg_H1),
        ('3Eg(H2)', e_3Eg_H2),
        ('3Eg(G1)', e_3Eg_G1),
        ('3Eg(G2)', e_3Eg_G2),
        ('1A1g', e_1A1g_I),
        ('1A1g(G)', e_1A1g_G),
        ('1A1g(S)', e_1A1g_S),
        ('1Eg(G)', e_1Eg_G),
        ('1Eg(I1)', e_1Eg_I1),
        ('1Eg(I2)', e_1Eg_I2),
        ('1T1g(G)', e_1T1g_G),
        ('1T1g(I)', e_1T1g_I),
        ('1T2g(G)', e_1T2g_G),
        ('1T2g(I1)', e_1T2g_I1),
        ('1T2g(I2)', e_1T2g_I2),
    ]
    
    # Sort by energy
    all_levels.sort(key=lambda x: x[1])
    
    return all_levels

# Compute for each Dq/B value
dq_over_b_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

print("Tanabe-Sugano Diagram for d⁶ Octahedral Ion")
print(f"Racah parameters: B = {B} cm⁻¹, C = {C} cm⁻¹, C/B = {C_over_B:.3f}")
print("=" * 60)

results = []
for dq_over_b in dq_over_b_values:
    levels = get_d6_energies(dq_over_b)
    
    # Ground state energy
    ground_energy = levels[0][1]
    
    # Express relative to ground
    relative_levels = [(label, e - ground_energy) for label, e in levels]
    relative_levels.sort(key=lambda x: x[1])
    
    # Take lowest 6
    lowest_6 = relative_levels[:6]
    results.append((dq_over_b, lowest_6))
    
    print(f"\nDq/B = {dq_over_b}:")
    for label, e in lowest_6:
        print(f"  {label}: E/B = {e:.4f}")

print("\n" + "=" * 60)
print("Summary table:")
print("=" * 60)
print(f"{'Dq/B':<6} {'Level 1':<12} {'E/B':<8} {'Level 2':<12} {'E/B':<8} {'Level 3':<12} {'E/B':<8}")
print("-" * 60)
for dq, levels in results:
    l1, e1 = levels[0]
    l2, e2 = levels[1]
    l3, e3 = levels[2]
    print(f"{dq:<6.1f} {l1:<12} {e1:<8.4f} {l2:<12} {e2:<8.4f} {l3:<12} {e3:<8.4f}")

print("\n" + "-" * 60)
print(f"{'Dq/B':<6} {'Level 4':<12} {'E/B':<8} {'Level 5':<12} {'E/B':<8} {'Level 6':<12} {'E/B':<8}")
print("-" * 60)
for dq, levels in results:
    l4, e4 = levels[3]
    l5, e5 = levels[4]
    l6, e6 = levels[5]
    print(f"{dq:<6.1f} {l4:<12} {e4:<8.4f} {l5:<12} {e5:<8.4f} {l6:<12} {e6:<8.4f}")
EOF
python3 final_results.py