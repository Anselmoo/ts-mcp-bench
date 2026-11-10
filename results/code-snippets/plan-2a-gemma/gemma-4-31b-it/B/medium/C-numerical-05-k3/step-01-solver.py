import numpy as np
from scipy.optimize import fsolve

def equations(vars, nu1, nu2, nu3, order):
    Dq, B = vars
    # Order 0: nu1 -> T2g, nu2 -> T1g(P), nu3 -> A2g
    # Order 1: nu1 -> T2g, nu2 -> A2g, nu3 -> T1g(P)
    
    # T1g eigenvalues
    # Matrix: [[-4*Dq, np.sqrt(480)*B], [np.sqrt(480)*B, 15*B - 4*Dq]]
    # Characteristic eq: (x + 4Dq)(x - 15B + 4Dq) - 480B^2 = 0
    # x^2 - (15B - 8Dq)x + (-4Dq)(15B - 4Dq) - 480B^2 = 0
    # x = [ (15B - 8Dq) +/- sqrt( (15B - 8Dq)^2 - 4(-60BDq + 16Dq^2 - 480B^2) ) ] / 2
    # x = [ 15B - 8Dq +/- sqrt( 225B^2 - 240BDq + 64Dq^2 + 240BDq - 64Dq^2 + 1920B^2 ) ] / 2
    # x = [ 15B - 8Dq +/- sqrt( 2145B^2 ) ] / 2
    
    x1 = (15*B - 8*Dq - np.sqrt(2145)*B) / 2
    x2 = (15*B - 8*Dq + np.sqrt(2145)*B) / 2
    
    e_t2g = -3*Dq
    e_a2g = 12*Dq
    
    if order == 0:
        # nu1 = T2g - T1g_low, nu2 = T1g_high - T1g_low, nu3 = A2g - T1g_low
        return [
            e_t2g - x1 - nu1,
            x2 - x1 - nu2,
            e_a2g - x1 - nu3
        ]
    elif order == 1:
        # nu1 = T2g - T1g_low, nu2 = A2g - T1g_low, nu3 = T1g_high - T1g_low
        return [
            e_t2g - x1 - nu1,
            e_a2g - x1 - nu2,
            x2 - x1 - nu3
        ]

nu = [15730, 24030, 32750]
for order in [0, 1]:
    # Try different starting guesses
    for guess in [(1000, 500), (500, 1000), (1500, 800)]:
        try:
            sol = fsolve(equations, guess, args=(nu[0], nu[1], nu[2], order))
            Dq, B = sol
            if Dq > 0 and B > 0:
                print(f"Order {order}, Guess {guess}: Dq={Dq:.2f}, B={B:.2f}")
        except:
            pass
