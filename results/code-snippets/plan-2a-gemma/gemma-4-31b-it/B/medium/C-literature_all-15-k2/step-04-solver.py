import numpy as np
from scipy.optimize import fsolve

def equations(Delta_o):
    nu1 = 8480
    nu3 = 20360
    # 15B = 3*Delta_o + 0.5*nu3 - nu1
    B = (3*Delta_o + 0.5*nu3 - nu1) / 15
    nu3_calc = np.sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
    return nu3_calc - nu3

sol = fsolve(equations, 7825)
Delta_o = sol[0]
B = (3*Delta_o + 0.5*20360 - 8480) / 15
print(f"Delta_o = {Delta_o:.2f}, B = {B:.2f}")
