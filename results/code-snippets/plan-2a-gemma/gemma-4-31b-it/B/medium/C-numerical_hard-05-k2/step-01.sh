cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    C = 4.5 * B
    
    # Common d6 low-spin formulas
    # nu1 = 10*Dq - 4*B + C
    # nu2 = 10*Dq + 6*B - C
    # nu3 = 20*Dq - 12*B + 2*C
    
    # We try different combinations of coefficients for nu3
    # nu3 = 20*Dq + c*B
    # But since we don't know c, let's just use nu1 and nu2 to find Dq, B
    # and see if nu3 fits.
    
    nu1_calc = 10*Dq - 4*B + C
    nu2_calc = 10*Dq + 6*B - C
    
    return (nu1_calc - 13960)**2 + (nu2_calc - 22740)**2

res = minimize(objective, [2000, 600], bounds=[(0, 10000), (0, 5000)])
print(res.x)
EOF
python3 solver.py
