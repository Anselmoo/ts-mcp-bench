cat << 'EOF' > solve_b.py
import numpy as np
from scipy.optimize import fsolve

def func(B):
    Dq = 352.35
    C = 4 * B
    X = 15*B + 10*C
    Y = 5*B + 4*C
    v1 = 0.5 * (X - np.sqrt(X**2 - 160*Dq*Y))
    return v1 - 19720

sol = fsolve(func, 800)
print(sol[0])
EOF
python3 solve_b.py
