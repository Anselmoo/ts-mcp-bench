import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B, C = p
    # Energy expressions for d5 High Spin
    # Nu1: 6A1g -> 4T1g(G)
    # Nu2: 6A1g -> 4T2g(G)
    # Nu3: 6A1g -> 4Eg(G)
    
    # Use the more precise formulas for d5
    # These formulas are relative to the 6A1g ground state.
    # Let X = 15B + 10C
    # Let Y = 5B + 4C
    X = 15*B + 10*C
    Y = 5*B + 4*C
    
    # The 4G state splits into 4T1g, 4T2g, 4Eg
    # The energies are the roots of a secular determinant.
    # For d5, the 4T1g and 4T1g(P) mix.
    # Let's use the simpler approximations first to see if they are consistent:
    # Nu2 = Nu1 + 10Dq
    # Nu3 = Nu1 + 15Dq
    # Nu1 = -10Dq + 0.5 * (X - sqrt(X**2 - 160*Dq*Y))
    
    # However, let's try to use the observed values:
    # Nu1 = 19720
    # Nu2 = 23260
    # Nu3 = 24980
    
    v1 = -10*Dq + 0.5 * (X - np.sqrt(X**2 - 160*Dq*Y))
    v2 = -10*Dq + 0.5 * (X + np.sqrt(X**2 - 160*Dq*Y)) - 5*Dq # This is an approximation
    # A better approach is to use the secular determinant for 4T1g(G) and 4T1g(P)
    # But for MnF2, Dq is small, so the 4T1g(G) state is primarily 4G.
    
    return [v1 - 19720, v2 - 23260, (v1 + 15*Dq) - 24980]

# Initial guesses
# From the manual calculation: Dq ~ 350, B ~ 700, C ~ 2800
p0 = [350, 700, 2800]
sol = fsolve(equations, p0)
print(sol)
