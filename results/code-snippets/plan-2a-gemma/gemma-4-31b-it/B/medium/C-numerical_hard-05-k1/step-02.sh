cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq10, B = params
    C = 4.5 * B
    
    # 1T2g energy
    nu2_calc = Dq10 + 16 * B + C
    
    # 1T1g matrix
    h11 = Dq10 - 4 * B + C
    h22 = 2 * Dq10 - 12 * B + 3 * C
    h12 = 4 * np.sqrt(2) * B
    
    # Eigenvalues of 1T1g matrix
    tr = h11 + h22
    det = h11 * h22 - h12**2
    
    # lambda = (tr +/- sqrt(tr^2 - 4det)) / 2
    gap = np.sqrt(max(0, tr**2 - 4 * det))
    nu1_calc = (tr - gap) / 2
    nu3_calc = (tr + gap) / 2
    
    return (nu1_calc - 13960)**2 + (nu2_calc - 22740)**2 + (nu3_calc - 29700)**2

res = minimize(objective, [15000, 400], bounds=[(10000, 20000), (200, 600)])
print(res.x)
EOF
python3 solution.py
