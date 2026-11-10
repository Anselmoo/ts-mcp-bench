cat << 'EOF' > plot_B.py
import numpy as np
import matplotlib.pyplot as plt

def get_nus(B):
    Dq = 901.0
    E_T2g = 10*Dq - 3*B
    E_A2g = 20*Dq - 3*B
    E_T1g_F_un = 0.5 * (-15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    E_T1g_P_un = 15*B
    trace = E_T1g_F_un + E_T1g_P_un
    det = E_T1g_F_un * E_T1g_P_un - (6*B)**2
    disc = np.sqrt(trace**2 - 4*det)
    E_ground = 0.5 * (trace - disc)
    E_T1g_P = 0.5 * (trace + disc)
    return E_T2g - E_ground, E_A2g - E_ground, E_T1g_P - E_ground

B_vals = np.linspace(100, 2000, 100)
nu1_vals = [get_nus(B)[0] for B in B_vals]
nu3_vals = [get_nus(B)[2] for B in B_vals]

for B, n1, n3 in zip(B_vals, nu1_vals, nu3_vals):
    print(f"B: {B:.1f}, nu1: {n1:.1f}, nu3: {n3:.1f}")
EOF
python3 plot_B.py
