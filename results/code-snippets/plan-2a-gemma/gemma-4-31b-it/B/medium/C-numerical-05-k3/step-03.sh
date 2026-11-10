cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import minimize

def get_energies(params):
    Dq, B = params
    # T1g eigenvalues
    # Matrix: [[-4*Dq, np.sqrt(480)*B], [np.sqrt(480)*B, 15*B - 4*Dq]]
    trace = 15*B - 8*Dq
    det = (-4*Dq)*(15*B - 4*Dq) - 480*B**2
    # lambda = [trace +/- sqrt(trace^2 - 4*det)] / 2
    disc = np.sqrt(max(0, trace**2 - 4*det))
    x1 = (trace - disc) / 2
    x2 = (trace + disc) / 2
    
    e_t2g = -3*Dq
    e_a2g = 12*Dq
    
    # The three spin-allowed transitions from x1
    # Order: T2g, T1g(P), A2g
    # But we don't know the order for sure. Let's sort them.
    energies = sorted([e_t2g - x1, x2 - x1, e_a2g - x1])
    return np.array(energies)

def objective(params):
    nu_obs = np.array([15730, 24030, 32750])
    nu_calc = get_energies(params)
    return np.sum((nu_obs - nu_calc)**2)

res = minimize(objective, [1000, 600], bounds=[(0, 5000), (0, 5000)])
print(f"Dq={res.x[0]:.2f}, B={res.x[1]:.2f}")
print(f"Calculated: {get_energies(res.x)}")
EOF
python3 solver.py
