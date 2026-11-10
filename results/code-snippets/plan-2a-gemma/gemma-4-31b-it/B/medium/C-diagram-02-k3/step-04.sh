cat << 'EOF' > solution.py
import numpy as np

def get_levels(dq_b):
    B = 1.0
    e_5eg = -6.0 * dq_b
    e_5t2g = 4.0 * dq_b
    e_3t1g_h1 = 9.0 - 4.0 * dq_b
    e_3t2g_h = 11.0 - 2.0 * dq_b
    e_3t1g_h2 = 13.0 - 4.0 * dq_b
    e_3a2g_h = 15.0 - 2.0 * dq_b
    e_1a1g_g = 22.0 - 16.0 * dq_b
    
    levels = [
        ('5Eg', e_5eg),
        ('5T2g', e_5t2g),
        ('3T1g', e_3t1g_h1),
        ('3T2g', e_3t2g_h),
        ('3T1g', e_3t1g_h2),
        ('3A2g', e_3a2g_h),
        ('1A1g', e_1a1g_g),
    ]
    
    levels.sort(key=lambda x: x[1])
    ground_e = levels[0][1]
    
    lowest_6 = levels[:6]
    return [(term, round(e - ground_e, 2)) for term, e in lowest_6]

for dq_b in np.arange(0, 4.5, 0.5):
    if dq_b > 4.0: break
    print(f"{dq_b:.1f} {get_levels(dq_b)}")
EOF
python3 solution.py
