import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    B, Dq = vars
    nu1_calc = 10 * Dq
    # Formula 1: nu2, nu3 are roots of E^2 - (15B + 10Dq)E + 100Dq^2 = 0 (Incorrect, just testing)
    # Formula 2: nu2, nu3 are roots of E^2 - (15B + 10Dq)E + 15B*10Dq = 0 (Incorrect)
    # Formula 3: 
    # E(4T2g) = 10Dq
    # E(4T1g(F)) = 0.5 * (15*B - 10*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    # E(4T1g(P)) = 0.5 * (15*B - 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)) + something?
    
    # Correct for d3:
    # E(4A2g) = -15B (relative to some origin)
    # E(4T2g) = -15B + 10Dq
    # E(4T1g) are roots of E^2 - (15B + 10Dq)E + 100Dq^2 = 0? No.
    
    # Let's try:
    # nu1 = 10*Dq
    # nu2 = 0.5 * (15*B + np.sqrt(225*B**2 + 120*B*10*Dq + (10*Dq)**2)) - 10*Dq
    # nu3 = 0.5 * (15*B - np.sqrt(225*B**2 + 120*B*10*Dq + (10*Dq)**2)) + 10*Dq? No.
    
    # Let's use the relation from a reliable source for d3 (e.g. Tanabe Sugano):
    # nu1 = 10 Dq
    # nu2 = 0.5 * (15*B + sqrt(225*B^2 + 120*B*10*Dq + (10*Dq)^2)) - 10*Dq (Wait, this is for d3?)
    # Actually, the roots for T1 are E = 0.5 * (15*B + 10*Dq +/- sqrt((15*B-10*Dq)^2 + 120*B*10*Dq))
    # nu2 = 0.5 * (15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    # nu3 = 0.5 * (15*B + 10*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq))
    
    # Let's check this.
    nu1_obs = 14170
    nu2_obs = 21710
    nu3_obs = 33970
    
    res1 = 10 * Dq - nu1_obs
    res2 = 0.5 * (15*B + 10*Dq - np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)) - nu2_obs
    res3 = 0.5 * (15*B + 10*Dq + np.sqrt((15*B - 10*Dq)**2 + 120*B*10*Dq)) - nu3_obs
    
    return [res1, res2] # Use nu1 and nu2 to solve for B, Dq, then check nu3

B_init = 700
Dq_init = 1417
sol = fsolve(equations, [B_init, Dq_init])
B_sol, Dq_sol = sol
nu1_calc = 10 * Dq_sol
nu2_calc = 0.5 * (15*B_sol + 10*Dq_sol - np.sqrt((15*B_sol - 10*Dq_sol)**2 + 120*B_sol*10*Dq_sol))
nu3_calc = 0.5 * (15*B_sol + 10*Dq_sol + np.sqrt((15*B_sol - 10*Dq_sol)**2 + 120*B_sol*10*Dq_sol))

print(f"B = {B_sol}, Dq = {Dq_sol}")
print(f"nu1 = {nu1_calc}, nu2 = {nu2_calc}, nu3 = {nu3_calc}")
