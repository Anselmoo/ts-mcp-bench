cat << 'EOF' > solver.py
import numpy as np

def solve_levels(x):
    # Quartet mixing
    # M = [[-6*x, 4*np.sqrt(6)*x], [4*np.sqrt(6)*x, 15]]
    # Eigenvalues:
    trace = 15 - 6*x
    det = 15 * (-6*x) - (4*np.sqrt(6)*x)**2
    # det = -90x - 96x^2
    
    # lambda = (trace +/- sqrt(trace^2 - 4*det)) / 2
    disc = np.sqrt(trace**2 - 4*det)
    l1 = (trace - disc) / 2
    l2 = (trace + disc) / 2
    
    # Energies relative to barycenter
    # E(^4T1g_F) = l1
    # E(^4T2g) = 4*x
    # E(^4A2g) = 12*x
    # E(^4T1g_P) = l2
    # E(^2Eg) = -18*x + 30
    # E(^2T1g) = -16*x + 30
    
    levels = [
        ('^4T1g', l1),
        ('^4T2g', 4*x),
        ('^4A2g', 12*x),
        ('^4T1g(P)', l2),
        ('^2Eg', -18*x + 30),
        ('^2T1g', -16*x + 30)
    ]
    
    # Ground state is the minimum
    ground_energy = min(l for term, l in levels)
    
    # Shift and sort
    shifted_levels = []
    for term, l in levels:
        shifted_levels.append((term, l - ground_energy))
    
    shifted_levels.sort(key=lambda x: x[1])
    return shifted_levels

for x in np.arange(0, 4.1, 0.5):
    res = solve_levels(x)
    print(f"{x:.1f}:")
    for term, e in res:
        print(f"  {term}: {e:.2f}")
EOF
python3 solver.py
