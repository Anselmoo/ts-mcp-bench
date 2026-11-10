cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def objective(params):
    Dq, B = params
    nu1 = 10 * Dq
    nu2 = 0.5 * (15*B + 30*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    nu3 = 0.5 * (15*B + 30*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*Dq**2))
    target = np.array([4070, 7030, 16400])
    calc = np.array([nu1, nu2, nu3])
    return np.sum((target - calc)**2)

res = minimize(objective, [400, 800], bounds=[(0, 2000), (0, 2000)])
print(f"Dq: {res.x[0]}, B: {res.x[1]}")
print(f"Calculated: {get_energies_new(res.x)}")
EOF
# Wait, I need to define get_energies_new
sed -i 's/print(f"Calculated: {get_energies_new(res.x)}")/print(f"Calculated: {np.array([10*res.x[0], 0.5*(15*res.x[1]+30*res.x[0]-np.sqrt((15*res.x[1]-10*res.x[0])**2+120*res.x[0]**2)), 0.5*(15*res.x[1]+30*res.x[0]+np.sqrt((15*res.x[1]-10*res.x[0])**2+120*res.x[0]**2))]}")/' solver.py
python3 solver.py
