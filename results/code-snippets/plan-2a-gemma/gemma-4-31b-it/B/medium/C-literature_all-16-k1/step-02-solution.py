import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    nu1 = 10 * Dq
    nu2 = 15*B + 0.5*(15*Dq - 3*B) - 0.5 * np.sqrt((15*Dq - 3*B)**2 + 120*B**2)
    nu3 = 15*B + 0.5*(15*Dq - 3*B) + 0.5 * np.sqrt((15*Dq - 3*B)**2 + 120*B**2)
    return [nu1 - 7400, nu2 - 12660] # Use nu1 and nu2 to find Dq, B

Dq_init, B_init = 740, 800
Dq_sol, B_sol = fsolve(equations, [Dq_init, B_init])
print(f"Dq: {Dq_sol[0]}, B: {B_sol[0]}")
# Now check nu3
Dq, B = Dq_sol
nu3 = 15*B + 0.5*(15*Dq - 3*B) + 0.5 * np.sqrt((15*Dq - 3*B)**2 + 120*B**2)
print(f"nu3: {nu3}")
