cat << 'EOF' > solution.py
import numpy as np

B = 551.0
C = 2511.0
gamma = C / B

def get_levels(x):
    # x = Dq/B
    # Approximate formulas for d^6 lowest levels
    # Ground state is ^5T2g
    e_5T2 = 0.0
    e_5Eg = 10.0 * x
    e_3T1g_F = 0.4 * gamma + 4.0 * x
    e_3T2g_F = 0.6 * gamma + 6.0 * x
    e_3A2g_F = 0.8 * gamma + 8.0 * x
    e_3T1g_P = 1.2 * gamma + 10.0 * x
    
    levels = [
        ('^5T2g', e_5T2),
        ('^5Eg', e_5Eg),
        ('^3T1g(F)', e_3T1g_F),
        ('^3T2g(F)', e_3T2g_F),
        ('^3A2g(F)', e_3A2g_F),
        ('^3T1g(P)', e_3T1g_P),
    ]
    levels.sort(key=lambda x: x[1])
    return levels

results = []
for dq_b in np.arange(0, 4.5, 0.5):
    if dq_b > 4.0: break
    levels = get_levels(dq_b)
    results.append({'dq_over_b': round(dq_b, 2), 'levels': levels})

for res in results:
    print(f"{res['dq_over_b']}: {res['levels']}")
EOF
python3 solution.py
