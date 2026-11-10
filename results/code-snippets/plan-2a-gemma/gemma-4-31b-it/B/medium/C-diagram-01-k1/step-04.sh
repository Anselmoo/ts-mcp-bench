cat << 'EOF' > solution.py
import numpy as np

def compute_levels(dq_over_b, c_over_b):
    B = 1.0
    Dq = dq_over_b * B
    C = c_over_b * B
    
    levels = []
    levels.append(('^4A2g', 0.0))
    levels.append(('^4T2g', 10.0 * dq_over_b))
    levels.append(('^4T1g', 20.0 * dq_over_b))
    levels.append(('^4T1g', 15.0))
    
    e_2g = 1.0 + 3.0 * c_over_b
    levels.append(('^2Eg', e_2g + 2.0 * dq_over_b))
    levels.append(('^2T1g', e_2g + 2.0 * dq_over_b))
    levels.append(('^2T2g', e_2g + 6.0 * dq_over_b))
    levels.append(('^2A1g', e_2g + 10.0 * dq_over_b))
    
    levels.sort(key=lambda x: x[1])
    return levels[:6]

c_over_b = 3390 / 828
for dq_b in np.arange(0, 4.5, 0.5):
    res = compute_levels(dq_b, c_over_b)
    print(f"{dq_b:.1f} {res}")
EOF
python3 solution.py
