cat << 'EOF' > solution.py
import numpy as np

def get_levels(dq_b):
    B = 1.0
    # Energies relative to barycenter
    e_5eg = -6.0 * dq_b
    e_5t2g = 4.0 * dq_b
    e_3t1g_h = 9.0 - 4.0 * dq_b
    e_3t2g_h = 11.0 - 2.0 * dq_b
    e_3a2g_h = 13.0 - 2.0 * dq_b
    e_1a1g_g = 22.0 - 16.0 * dq_b
    e_3t1g_f = 15.0 - 4.0 * dq_b
    
    levels = [
        ('5Eg', e_5eg),
        ('5T2g', e_5t2g),
        ('3T1g', e_3t1g_h),
        ('3T2g', e_3t2g_h),
        ('3A2g', e_3a2g_h),
        ('1A1g', e_1a1g_g),
        ('3T1g', e_3t1g_f),
    ]
    # To handle terms of the same symmetry from different free-ion terms, 
    # I'll keep them separate by adding the origin term to the label.
    # But the prompt says "term label", let's use 3T1g(H), etc. if needed.
    # "terms of the same symmetry that come from different free-ion terms are separate levels"
    
    levels = [
        ('5Eg', e_5eg),
        ('5T2g', e_5t2g),
        ('3T1g', e_3t1g_h),
        ('3T2g', e_3t2g_h),
        ('3A2g', e_3a2g_h),
        ('1A1g', e_1a1g_g),
        ('3T1g', e_3t1g_f),
    ]
    
    # The ground state at Dq/B=0 is 5D, which splits into 5Eg and 5T2g.
    # Since they both come from 5D and are at the same energy at Dq/B=0,
    # we should list them both.
    
    levels.sort(key=lambda x: x[1])
    ground_e = levels[0][1]
    
    # Take the lowest 6
    lowest_6 = levels[:6]
    return [(term, round(e - ground_e, 2)) for term, e in lowest_6]

for dq_b in np.arange(0, 4.5, 0.5):
    if dq_b > 4.0: break
    print(f"{dq_b:.1f} {get_levels(dq_b)}")
EOF
python3 solution.py
