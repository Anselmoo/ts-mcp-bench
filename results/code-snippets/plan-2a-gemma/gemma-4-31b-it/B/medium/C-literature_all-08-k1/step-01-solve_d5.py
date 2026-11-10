import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B, C = p
    # Energy of 6A1g = -10*Dq
    # Energy of 4Eg, 4A1g = 10*B + 0.5*(2*C - 3*B)
    # Energy of 4T2g = 10*B + 0.5*(2*C - 3*B) - 10*Dq
    # Energy of 4T1g is the lowest root of the 3x3 matrix for T1g states.
    # However, a common approximation is used for the 4T1g(G) state:
    # E(4T1g) = -10*Dq + 10*B + 0.5*(2*C - 3*B) - sqrt(25*Dq**2 + 100*B**2 - 100*B*Dq + ...)
    # Actually, let's use the simplified transitions for d5 high spin:
    # nu1 = E(4T1g) - E(6A1g)
    # nu2 = E(4T2g) - E(6A1g)
    # nu3 = E(4Eg) - E(6A1g)
    
    # Simplified approximations from some literature:
    # nu2 = 8.5*B + C
    # nu3 = nu2 + 10*Dq
    # nu1 = nu2 - 10*Dq - something?
    
    # Let's try the ones from a reliable source:
    # nu3 = 10*B + (C - 1.5*B) + 10*Dq
    # nu2 = 10*B + (C - 1.5*B)
    # nu1 = E(4T1g) - E(6A1g)
    
    # For 4T1g, we have the matrix:
    # H = [ [E(4T1g(G)), V1, V2],
    #       [V1, E(4T1g(P)), V3],
    #       [V2, V3, E(4T1g(F))] ]
    # But often we can use the approximation for low Dq:
    # nu1 = 8.5*B + C - 10*Dq - sqrt(25*Dq**2 + (10*B)**2 - 100*B*Dq)
    # This is too rough.
    
    # Let's use the energy expressions for the 4G term split in Oh:
    # E(4T1g) = -10*Dq + E(4G) - something
    # E(4T2g) = 0*Dq + E(4G)
    # E(4Eg) = 10*Dq + E(4G)
    # Then nu1 = E(4T1g) - (-10*Dq) = E(4G) - something
    # nu2 = E(4T2g) - (-10*Dq) = E(4G) + 10*Dq
    # nu3 = E(4Eg) - (-10*Dq) = E(4G) + 20*Dq
    # Checking: nu3 - nu2 = 10*Dq, nu2 - nu1 = something.
    # 23370 - 22130 = 1240 = 10*Dq => Dq = 124.
    # nu2 = E(4G) + 1240 = 22130 => E(4G) = 20890.
    # nu1 = 19180.
    
    # Let's use the formula for E(4T1g) for d5:
    # E(4T1g) = -10*Dq + (10*B + (C - 1.5*B)) - sqrt(25*Dq**2 + 100*B**2 - 100*B*Dq + 2*(2*C-3*B)*(10*B-10*Dq))
    # This is from a specific paper. Let's try it.
    # E(6A1g) = -10*Dq
    # nu1 = E(4T1g) - E(6A1g) = 10*B + (C - 1.5*B) - sqrt(...)
    # nu2 = E(4T2g) - E(6A1g) = 10*B + (C - 1.5*B) + 10*Dq - 10*Dq = 10*B + (C - 1.5*B) ??
    # No, E(4T2g) = E(4G) relative to barycenter.
    # E(6A1g) = -10*Dq.
    # E(4T2g) = E(4G).
    # E(4Eg) = E(4G) + 10*Dq.
    # nu2 = E(4G) - (-10*Dq) = E(4G) + 10*Dq.
    # nu3 = E(4G) + 10*Dq - (-10*Dq) = E(4G) + 20*Dq.
    # nu3 - nu2 = 10*Dq.
    # nu2 = 22130, nu3 = 23370 => 10*Dq = 1240 => Dq = 124.
    # E(4G) = 22130 - 1240 = 20890.
    # 8.5*B + C = 20890.
    
    # Now nu1 = E(4T1g) - (-10*Dq) = -10*Dq + E(4G) - sqrt(...) + 10*Dq = E(4G) - sqrt(...)
    # nu1 = 19180.
    # sqrt(...) = 20890 - 19180 = 1710.
    # 25*Dq**2 + 100*B**2 - 100*B*Dq + 2*(2*C-3*B)*(10*B-10*Dq) = 1710**2.
    
    # We have:
    # 1) 10*Dq = 1240
    # 2) 8.5*B + C = 20890
    # 3) 25*Dq**2 + 100*B**2 - 100*B*Dq + 2*(2*C-3*B)*(10*B-10*Dq) = 1710**2
    
    # From (2), C = 20890 - 8.5*B.
    # Substitute C into (3):
    # 25*(124**2) + 100*B**2 - 100*B*124 + 2*(2*(20890 - 8.5*B) - 3*B)*(10*B - 1240) = 1710**2
    # 384400 + 100*B**2 - 12400*B + 2*(41780 - 17*B - 3*B)*(10*B - 1240) = 2924100
    # 100*B**2 - 12400*B + 2*(41780 - 20*B)*(10*B - 1240) = 2539700
    # 100*B**2 - 12400*B + 2*(417800*B - 51759200 - 200*B**2 + 24800*B) = 2539700
    # 100*B**2 - 12400*B + 835600*B - 103518400 - 400*B**2 + 49600*B = 2539700
    # -300*B**2 + 872800*B - 103518400 = 2539700
    # 300*B**2 - 872800*B + 106058100 = 0
    
    return [0, 0, 0]

# Solve the quadratic: 300*B**2 - 872800*B + 106058100 = 0
import math
a = 300
b = -872800
c = 106058100
delta = b**2 - 4*a*c
B1 = (-b + math.sqrt(delta)) / (2*a)
B2 = (-b - math.sqrt(delta)) / (2*a)
print(f"B1: {B1}, B2: {B2}")
