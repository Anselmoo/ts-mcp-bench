import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    term = np.sqrt((15*B)**2 + 1440*Dq**2)
    nu1 = 10*Dq + 0.5 * (term - 15*B)
    nu2 = term
    return [nu1 - 17500, nu2 - 25000]

sol = fsolve(equations, [1500, 800])
print(f"Dq: {sol[0]}, B: {sol[1]}")
