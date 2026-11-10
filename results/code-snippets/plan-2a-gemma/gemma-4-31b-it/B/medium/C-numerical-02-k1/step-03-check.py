import numpy as np

def get_energies(params):
    Dq, B = params
    Delta_o = 10 * Dq
    L1 = (15*B - np.sqrt(Delta_o**2 + 30*Delta_o*B + 369*B**2)) / 2
    L2 = (15*B + np.sqrt(Delta_o**2 + 30*Delta_o*B + 369*B**2)) / 2
    return np.array([
        -0.5*Delta_o + 6*B - L1,
        6*B - L1,
        L2 - L1
    ])

print(get_energies([630.076, 1057.522]))
