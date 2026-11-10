cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import fsolve

def equations(p, nu1, nu2, nu3):
    Dq, B = p
    # nu1 = 10 * Dq
    # nu2 = 0.5 * (15*Dq + 30*B - np.sqrt((15*Dq - 30*B)**2 + 120*Dq*B))
    # nu3 = 0.5 * (15*Dq + 30*B + np.sqrt((15*Dq - 30*B)**2 + 120*Dq*B))
    return [
        10*Dq - nu1,
        0.5 * (15*Dq + 30*B - np.sqrt((15*Dq - 30*B)**2 + 120*Dq*B)) - nu2
    ]

# Test assignments
bands = [9770, 16050, 26740, 12987]
# Case 1: nu1=9770, nu2=16050, nu3=26740, nu_1E=12987
# Case 2: nu1=9770, nu2=12987, nu3=26740, nu_1E=16050
# Case 3: nu1=12987, nu2=16050, nu3=26740, nu_1E=9770 (unlikely)

for nu1, nu2, nu3, nu_1E in [(9770, 16050, 26740, 12987), (9770, 12987, 26740, 16050)]:
    print(f"Testing nu1={nu1}, nu2={nu2}, nu3={nu3}, nu_1E={nu_1E}")
    try:
        sol = fsolve(equations, [nu1/10, 800], args=(nu1, nu2, nu3))
        Dq, B = sol
        nu3_calc = 0.5 * (15*Dq + 30*B + np.sqrt((15*Dq - 30*B)**2 + 120*Dq*B))
        print(f"  Dq={Dq:.2f}, B={B:.2f}, nu3_calc={nu3_calc:.2f} (target {nu3})")
    except Exception as e:
        print(f"  Error: {e}")

EOF
python3 solution.py
