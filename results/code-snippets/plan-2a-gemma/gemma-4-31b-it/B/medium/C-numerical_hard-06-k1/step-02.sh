cat << 'EOF' > fit.py
import numpy as np
from scipy.optimize import least_squares

def residuals(vars):
    Dq, B = vars
    nu1_calc = 10*Dq - 4*B
    nu2_calc = 10*Dq + 6*B
    nu3_calc = 20*Dq - 6*B
    return [nu1_calc - 16700, nu2_calc - 26330, nu3_calc - 35020]

res = least_squares(residuals, [2000, 1000])
print(res.x)
EOF
python3 fit.py
