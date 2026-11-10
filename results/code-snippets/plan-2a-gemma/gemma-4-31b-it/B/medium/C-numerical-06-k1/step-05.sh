cat << 'EOF' > solution.py
import numpy as np

def check(Dq, B):
    Delta = 10 * Dq
    term = (15*B - Delta)**2 + 24*B*Delta
    sqrt_term = np.sqrt(term)
    e_t1g_f = 0.5 * (15*B - Delta - sqrt_term)
    e_t1g_p = 0.5 * (15*B - Delta + sqrt_term)
    e_t2g = 0.5 * Delta
    e_a2g = 1.5 * Delta + 6*B
    return [e_t2g - e_t1g_f, e_a2g - e_t1g_f, e_t1g_p - e_t1g_f]

for B in np.linspace(400, 1500, 500):
    for Dq in np.linspace(400, 1500, 500):
        v = check(Dq, B)
        if abs(v[0] - 9180) < 100 and abs(v[1] - 19550) < 100 and abs(v[2] - 20320) < 100:
            print(Dq, B)
EOF
python3 solution.py
