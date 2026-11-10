import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    nu2 = 15*B + 0.5*(15*Dq - 3*B) - 0.5 * np.sqrt((15*Dq - 3*B)**2 + 120*B**2)
    return [nu1 - 7400, nu2 - 12660]

sol = fsolve(equations, [740, 800])
Dq, B = sol
nu3 = 15*B + 0.5*(15*Dq - 3*B) + 0.5 * np.sqrt((15*Dq - 3*B)**2 + 120*B**2)
print(f"Dq: {Dq}, B: {B}, nu3: {nu3}")
