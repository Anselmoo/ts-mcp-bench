cat << 'EOF' > solution.py
import numpy as np

def solve_dq_b(nu1, nu2, nu3, c_over_b):
    # For d2 complexes:
    # The three lowest spin-allowed transitions from 3T1g are to 3T2g, 3T1g(P), and 3A2g.
    # According to several sources, for d2 (which is isomorphic to d4 low spin):
    # nu1 (3T1g -> 3T2g) = 10Dq - 3B
    # nu3 (3T1g -> 3A2g) = 10Dq + 5B
    # nu2 (3T1g -> 3T1g(P)) is more complex due to mixing.
    
    # Let's try the simple linear approximations first:
    # nu3 - nu1 = 8B
    # 24580 - 22900 = 1680
    # 8B = 1680 => B = 210
    # 10Dq = nu1 + 3B = 22900 + 3*210 = 22900 + 630 = 23530 => Dq = 2353
    # Then check nu2: nu2 = 10Dq + B = 23530 + 210 = 23740.
    # The given nu2 is 23730. This is extremely close!
    
    B = (nu3 - nu1) / 8
    Dq = (nu1 + 3*B) / 10
    calc_nu2 = 10*Dq + B
    return Dq, B, calc_nu2

nu1 = 22900
nu2 = 23730
nu3 = 24580
C_B = 4.3
dq, b, nu2_calc = solve_dq_b(nu1, nu2, nu3, C_B)
print(f"Dq: {dq}, B: {b}, nu2_calc: {nu2_calc}")
EOF
python3 solution.py
