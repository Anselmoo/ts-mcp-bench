import numpy as np
from scipy.optimize import fsolve

def equations(p):
    B, Dq = p
    Delta_o = 10 * Dq
    
    nu3_calc = np.sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
    nu1_calc = 3*Delta_o - 15*B + 0.5 * nu3_calc
    nu2_calc = 4*Delta_o - 15*B + 0.5 * nu3_calc
    
    # We have three observables, but only two parameters B and Dq.
    # Let's fit nu1 and nu3, and check nu2.
    # Or use a least squares fit.
    return [nu1_calc - 8480, nu3_calc - 20360]

B_guess, Dq_guess = 700, 782.5
sol = fsolve(equations, [B_guess, Dq_guess])
B, Dq = sol
Delta_o = 10 * Dq
nu3_calc = np.sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
nu1_calc = 3*Delta_o - 15*B + 0.5 * nu3_calc
nu2_calc = 4*Delta_o - 15*B + 0.5 * nu3_calc

print(f"B = {B:.2f}, Dq = {Dq:.2f}, Delta_o = {Delta_o:.2f}")
print(f"nu1 = {nu1_calc:.2f}, nu2 = {nu2_calc:.2f}, nu3 = {nu3_calc:.2f}")
