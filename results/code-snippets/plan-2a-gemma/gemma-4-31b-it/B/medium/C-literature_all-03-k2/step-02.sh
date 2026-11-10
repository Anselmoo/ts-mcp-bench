cat << 'EOF' > ts_d3.py
import numpy as np

def get_nu_ratios(B_over_Dq):
    # Fixed Dq = 1
    Dq = 1.0
    B = B_over_Dq
    
    # Energy of A2 is -15*Dq
    # Energy of T2 is -5*Dq
    # nu1 = 10*Dq = 10
    
    # T1 states are roots of the matrix:
    # [ 0, 6*B ]
    # [ 6*B, 15*B - 20*Dq ]  <-- relative to some origin?
    # No, let's use the eigenvalues of the T1 matrix:
    # The eigenvalues of the matrix:
    # [ 15*Dq, 6*B ]
    # [ 6*B, 15*B + 15*Dq ]
    # nu2, nu3 are the roots.
    
    matrix = np.array([[15*Dq, 6*B], [6*B, 15*B + 15*Dq]])
    eigvals = np.linalg.eigvalsh(matrix)
    nu2 = eigvals[0]
    nu3 = eigvals[1]
    
    return nu2/10, nu3/10

for b_dq in np.linspace(0.1, 2.0, 20):
    r2, r3 = get_nu_ratios(b_dq)
    print(f"B/Dq: {b_dq:.2f}, nu2/nu1: {r2:.3f}, nu3/nu1: {r3:.3f}")
EOF
python3 ts_d3.py
