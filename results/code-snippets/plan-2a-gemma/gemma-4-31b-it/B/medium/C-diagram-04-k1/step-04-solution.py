import numpy as np

B = 551.0
C = 2511.0
gamma = C / B

def get_levels(x):
    # x = Dq/B
    # Approximate energies relative to ^5T2g at x=0
    e_5T2 = 0.0 # Actually, ^5T2g is -4Dq, but we set it to 0 at x=0
    # But it depends on x: E(^5T2g) = -4Dq
    # E(^5Eg) = 6Dq
    # E(^1A1g) = -12Dq + 2B + C (approx)
    
    # Let's use energies relative to the center of gravity
    e_5T2_abs = -4.0 * x
    e_5Eg_abs = 6.0 * x
    e_1A1g_abs = -12.0 * x + (2.0 + gamma)
    e_3T1g_F_abs = 0.4 * gamma + 4.0 * x # Rough
    e_3T2g_F_abs = 0.6 * gamma + 6.0 * x # Rough
    e_3A2g_F_abs = 0.8 * gamma + 8.0 * x # Rough
    e_3T1g_P_abs = 1.2 * gamma + 10.0 * x # Rough
    
    levels_abs = [
        ('^5T2g', e_5T2_abs),
        ('^5Eg', e_5Eg_abs),
        ('^1A1g', e_1A1g_abs),
        ('^3T1g(F)', e_3T1g_F_abs),
        ('^3T2g(F)', e_3T2g_F_abs),
        ('^3A2g(F)', e_3A2g_F_abs),
        ('^3T1g(P)', e_3T1g_P_abs),
    ]
    
    # Ground state is the lowest
    ground_e = min(l[1] for l in levels_abs)
    
    # Relative energies
    levels_rel = []
    for term, e in levels_abs:
        levels_rel.append((term, e - ground_e))
    
    levels_rel.sort(key=lambda x: x[1])
    return levels_rel[:6]

results = []
for dq_b in np.arange(0, 4.5, 0.5):
    if dq_b > 4.0: break
    levels = get_levels(dq_b)
    results.append({'dq_over_b': round(dq_b, 2), 'levels': levels})

for res in results:
    print(f"{res['dq_over_b']}: {res['levels']}")
