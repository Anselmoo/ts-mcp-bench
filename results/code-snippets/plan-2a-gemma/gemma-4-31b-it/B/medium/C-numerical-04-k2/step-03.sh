cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(Dq, B):
    # Matrix for T1g(F) and T1g(P)
    # H11 = -6*Dq, H22 = 15*B, H12 = 6*B
    # This is a common form, but let's be careful.
    mat = np.array([[-6*Dq, 6*B], [6*B, 15*B]])
    eigvals = np.linalg.eigvalsh(mat)
    E_T1g_F = eigvals[0]
    E_T1g_P = eigvals[1]
    E_T2g = -4*Dq
    E_A2g = 6*Dq
    return E_T1g_F, E_T2g, E_A2g, E_T1g_P

def objective(params):
    Dq, B = params
    if Dq < 0 or B < 0: return 1e10
    E_T1g_F, E_T2g, E_A2g, E_T1g_P = get_energies(Dq, B)
    
    nu1 = E_T2g - E_T1g_F
    nu2 = E_A2g - E_T1g_F
    nu3 = E_T1g_P - E_T1g_F
    
    return (nu1 - 8620)**2 + (nu2 - 18410)**2 + (nu3 - 20250)**2

res = minimize(objective, [979, 800], method='Nelder-Mead')
Dq_opt, B_opt = res.x
E_T1g_F, E_T2g, E_A2g, E_T1g_P = get_energies(Dq_opt, B_opt)
print(f"Dq: {Dq_opt}, B: {B_opt}")
print(f"nu1: {E_T2g - E_T1g_F}, nu2: {E_A2g - E_T1g_F}, nu3: {E_T1g_P - E_T1g_F}")
EOF
python3 solver.py
