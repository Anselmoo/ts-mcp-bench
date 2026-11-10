import numpy as np

nu1 = 19170
nu2 = 27260
nu3 = 42610
Dq = nu1 / 10.0

for B in np.arange(600, 1200, 1):
    # Matrix: [[15*Dq - B, sqrt(12)*B], [sqrt(12)*B, 15*B]]
    # Eigenvalues:
    # trace = 15*Dq + 14*B
    # det = (15*Dq - B)(15*B) - 12*B^2 = 225*Dq*B - 15*B^2 - 12*B^2 = 225*Dq*B - 27*B^2
    # X^2 - trace*X + det = 0
    trace = 15 * Dq + 14 * B
    det = 225 * Dq * B - 27 * B**2
    delta = trace**2 - 4 * det
    if delta >= 0:
        x1 = (trace - np.sqrt(delta)) / 2
        x2 = (trace + np.sqrt(delta)) / 2
        if abs(x1 - nu2) < 100 and abs(x2 - nu3) < 100:
            print(f"Dq: {Dq}, B: {B}, x1: {x1}, x2: {x2}")
