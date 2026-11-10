import numpy as np
from scipy.optimize import least_squares

def residuals(vars):
    Dq, B = vars
    nu1 = 10 * Dq - 4 * B
    nu2 = 20 * Dq - 12 * B
    nu3 = 15 * B + 10 * Dq
    return [nu1 - 15730, nu2 - 24030, nu3 - 32750]

sol = least_squares(residuals, [2000, 1000])
print(f"Dq: {sol.x[0]}, B: {sol.x[1]}")
