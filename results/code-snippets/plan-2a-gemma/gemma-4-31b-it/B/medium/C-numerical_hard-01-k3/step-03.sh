cat << 'EOF' > solve_d4.py
import numpy as np

def solve_for_B_Dq(nu1, nu2, nu3):
    # Try various models for the transitions
    # Model 1: nu1 = 10Dq - 3B, nu2 = 10Dq + 2B, nu3 = 10Dq + 7B
    # 5B = nu2 - nu1
    B = (nu2 - nu1) / 5
    Dq10 = nu2 - 2*B
    return Dq10, B

nu1, nu2, nu3 = 18850, 19750, 20560
dq, b = solve_for_B_Dq(nu1, nu2, nu3)
print(f"Dq10: {dq}, B: {b}")
EOF
python3 solve_d4.py
