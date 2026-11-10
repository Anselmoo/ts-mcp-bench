import numpy as np
from scipy.optimize import least_squares

def residuals(vars):
    Dq, B = vars
    nu1 = 8 * Dq - B
    nu2 = 18 * Dq - 9 * B
    nu3 = 15 * B + 8 * Dq
    return [nu1 - 15730, nu2 - 24030, nu3 - 32750]

sol = least_squares(residuals, [2000, 1000])
print(f"Dq: {sol.x[0]}, B: {sol.x[1]}")
