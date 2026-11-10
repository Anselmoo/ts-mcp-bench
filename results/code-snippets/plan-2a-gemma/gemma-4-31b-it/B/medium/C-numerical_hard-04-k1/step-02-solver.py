import numpy as np
from scipy.optimize import fsolve

def equations(vars):
    Dq, B = vars
    C = 4.4 * B
    # Potential formulas for d5 low spin
    # nu1 = 10*Dq - 4*B - 0.5*(C - 3*B)
    # nu2 = 10*Dq - 4*B + 0.5*(C - 3*B)
    # nu3 = ?
    # Let's try nu3 = 10*Dq + some_coeff * B
    # Based on the difference nu3 - nu2 = 31640 - 29620 = 2020
    # nu3 - nu2 = (some_coeff + 4 - 0.5*(C/B - 3)) * B
    # 2020 = (some_coeff + 4 - 0.5*(4.4 - 3)) * B
    # 2020 = (some_coeff + 4 - 0.7) * B = (some_coeff + 3.3) * B
    # Also nu2 - nu1 = (C - 3*B) = 1.4 * B = 260 => B = 185.7
    # Then 2020 = (some_coeff + 3.3) * 185.7 => some_coeff + 3.3 = 10.87 => some_coeff = 7.57
    # This doesn't seem like a standard coefficient.
    return [0, 0]

# Let's try another set of formulas:
# Maybe nu1, nu2, nu3 are 10Dq - 4B, 10Dq - 4B + (C-3B), 10Dq - 4B + ...
# Let's try:
# nu1 = 10*Dq - 4*B
# nu2 = 10*Dq - 4*B + (C - 3*B) = 10*Dq - 7*B + C
# nu3 = 10*Dq + B
# Let's test this.
# nu2 - nu1 = C - 3*B = 1.4*B = 260 => B = 185.7
# nu3 - nu1 = 5*B = 5 * 185.7 = 928.5. But nu3 - nu1 = 2280.

# What if nu1 = 10*Dq - 4*B, nu2 = 10*Dq - 4*B + (C-3*B), nu3 = 10*Dq + 5*B?
# nu2 - nu1 = 1.4*B = 260 => B = 185.7
# nu3 - nu1 = 9*B = 9 * 185.7 = 1671. Still not 2280.

# What if nu3 = 10*Dq + 8*B?
# nu3 - nu1 = 12*B = 12 * 185.7 = 2228.4. This is very close to 2280!
# Let's check: 2280 / 185.7 = 12.27.
