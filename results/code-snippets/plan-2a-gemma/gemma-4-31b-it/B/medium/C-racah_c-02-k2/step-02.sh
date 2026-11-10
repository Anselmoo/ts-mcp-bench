cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def get_evals(Dq, B):
    matrix = np.array([[15*Dq, np.sqrt(120)*Dq], [np.sqrt(120)*Dq, 30*B]])
    return np.sort(np.linalg.eigvals(matrix))

def objective(B):
    Dq = 1449
    nu2_obs = 20430
    nu3_obs = 32030
    evals = get_evals(Dq, B)
    return (evals[0] - nu2_obs)**2 + (evals[1] - nu3_obs)**2

from scipy.optimize import minimize_scalar
res = minimize_scalar(objective, bounds=(0, 2000), method='bounded')
B_best = res.x
evals_best = get_evals(1449, B_best)
print(f"B = {B_best}")
print(f"nu2 = {evals_best[0]}, nu3 = {evals_best[1]}")
EOF
python3 solver.py
