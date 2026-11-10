cat << 'EOF' > solver.py
from scipy.optimize import fsolve

def equations(vars, nu1, nu2, nu3):
    Dq, B = vars
    # Note: we have 3 equations and 2 unknowns.
    # We should probably not assume nu1 = 10 Dq if it's not a perfect fit.
    # But the problem usually expects these formulas.
    # Let's use a least-squares approach.
    return [
        10*Dq - nu1,
        15*B + 20*Dq - (nu2 + nu3),
        225*B**2 - 600*B*Dq + 520*Dq**2 - (nu3 - nu2)**2
    ]

nu1, nu2, nu3 = 4330, 7520, 18640
# We'll minimize the sum of squares.
from scipy.optimize import minimize

def objective(vars):
    Dq, B = vars
    return (10*Dq - nu1)**2 + (15*B + 20*Dq - (nu2 + nu3))**2 + (225*B**2 - 600*B*Dq + 520*Dq**2 - (nu3 - nu2)**2)**2

res = minimize(objective, [433, 1166])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
EOF
python3 solver.py
