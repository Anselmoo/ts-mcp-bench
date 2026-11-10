cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def objective(vars, nu1, nu2, nu3):
    Dq, B = vars
    # Model:
    # nu1 = 8 * Dq
    # nu2 and nu3 are eigenvalues of:
    # [ 12*Dq, 6*B ]
    # [ 6*B, 15*B + 12*Dq ]
    
    # However, is it 8 Dq or 10 Dq?
    # Let's try both models.
    
    mat = np.array([[12*Dq, 6*B], [6*B, 15*B + 12*Dq]])
    eigvals = np.linalg.eigvalsh(mat)
    
    return (8*Dq - nu1)**2 + (eigvals[0] - nu2)**2 + (eigvals[1] - nu3)**2

nu1, nu2, nu3 = 4330, 7520, 18640
res = minimize(objective, [500, 600], args=(nu1, nu2, nu3))
print(f"Model 8Dq -> Dq: {res.x[0]}, B: {res.x[1]}")

def objective2(vars, nu1, nu2, nu3):
    Dq, B = vars
    # Model 10Dq:
    # nu1 = 10 * Dq
    # T1(F) unperturbed relative to A2 is 20 Dq? 
    # Let's check the ratio again.
    # If A2 is -12, T2 is -4, T1 is 0.
    # If we redefine Dq such that nu1 = 10 Dq, then:
    # nu1 = 10 Dq -> 8 Dq_old = 10 Dq_new -> Dq_old = 1.25 Dq_new
    # Then E(T1(F)) - E(A2) = 12 Dq_old = 12 * 1.25 Dq_new = 15 Dq_new.
    # And E(T1(P)) - E(A2) = 15 B + 12 Dq_old = 15 B + 15 Dq_new.
    # Mixing = 6 B.
    
    mat = np.array([[15*Dq, 6*B], [6*B, 15*B + 15*Dq]])
    eigvals = np.linalg.eigvalsh(mat)
    
    return (10*Dq - nu1)**2 + (eigvals[0] - nu2)**2 + (eigvals[1] - nu3)**2

res2 = minimize(objective2, [400, 600], args=(nu1, nu2, nu3))
print(f"Model 10Dq -> Dq: {res2.x[0]}, B: {res2.x[1]}")
EOF
python3 solver.py
