cat << 'EOF' > solve_lf.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    Dq, B = p
    Delta = 10 * Dq
    
    # Energy of quartet states relative to free-ion 4F
    # Using expressions derived for d3 (hole equivalent to d7)
    # For d3: E(4A2g)=0, E(4T2g)=Delta, E(4T1g(F)) = 0.5*(15B + Delta) - 0.5*sqrt(225B^2 + 120Dq^2 - 180BDq)
    # E(4T1g(P)) = 15B + 0.5*(15B + Delta) + 0.5*sqrt(225B^2 + 120Dq^2 - 180BDq)
    # However, d7 has 4T1g(F) as ground state.
    
    # Let's use the formula for d7 transitions:
    # nu1 = E(4T2g) - E(4T1g(F))
    # nu2 = E(4A2g) - E(4T1g(F))
    # nu3 = E(4T1g(P)) - E(4T1g(F))
    
    # E(4T1g(F)) = -1.5*B - 0.5*Delta + 0.5*np.sqrt(2.25*B**2 + 1.2*Delta**2 - 1.8*B*Delta)
    # E(4T2g) = -Delta
    # E(4A2g) = -Delta + 15*B # This is not correct.
    # Let's use the d3 shifted ones:
    
    # For d7, the levels are shifted by a constant.
    # Let's use the relative differences from d3:
    # nu1 = E(4T2g) - E(4T1g(F)) = Delta - [0.5*(15*B + Delta) - 0.5*np.sqrt(225*B**2 + 120*Dq**2 - 180*B*Dq)]
    # nu2 = E(4A2g) - E(4T1g(F)) = 0 - [0.5*(15*B + Delta) - 0.5*np.sqrt(225*B**2 + 120*Dq**2 - 180*B*Dq)]
    # This makes nu2 negative, which is impossible.
    
    # Correct d7 levels relative to 4T1g(F) = 0:
    # E(4T1g(F)) = 0
    # E(4T2g) = Delta - [0.5*(15*B + Delta) - 0.5*np.sqrt(225*B**2 + 120*Dq**2 - 180*B*Dq)]
    # E(4A2g) = 0? No.
    # Let's use the formula: nu2 - nu1 = Delta.
    # nu1 = 6150, nu2 = 12400 -> Delta = 6250.
    # Then nu1 = 6150 = Delta - [0.5*(15*B + Delta) - 0.5*sqrt()]
    # 6150 = 6250 - 0.5*(15*B + 6250) + 0.5*sqrt()
    # 0.5*(15*B + 6250) - 100 = 0.5*sqrt()
    # 15*B + 6250 - 200 = sqrt()
    # 15*B + 6050 = sqrt(225*B**2 + 120*Dq**2 - 180*B*Dq)
    # Square: 225*B**2 + 181500*B + 36602500 = 225*B**2 + 120*Dq**2 - 180*B*Dq
    # 181500*B + 180*B*Dq = 120*Dq**2 - 36602500
    
    # For nu3:
    # nu3 = E(4T1g(P)) - E(4T1g(F)) = [15*B + 0.5*(15*B + Delta) + 0.5*sqrt()] - [0.5*(15*B + Delta) - 0.5*sqrt()]
    # nu3 = 15*B + sqrt(225*B**2 + 120*Dq**2 - 180*B*Dq)
    # 16850 = 15*B + sqrt(...)
    # sqrt(...) = 16850 - 15*B
    
    # Now we have:
    # 1) sqrt(...) = 15*B + 6050
    # 2) sqrt(...) = 16850 - 15*B
    # 15*B + 6050 = 16850 - 15*B
    # 30*B = 10800
    # B = 360
    
    # Now find Delta from 15*B + 6050 = sqrt(225*B**2 + 1.2*Delta**2 - 1.8*B*Delta)
    # 15(360) + 6050 = 5400 + 6050 = 11450
    # 11450**2 = 225*(360**2) + 1.2*Delta**2 - 1.8*360*Delta
    # 131,102,500 = 29,160,000 + 1.2*Delta**2 - 648*Delta
    # 1.2*Delta**2 - 648*Delta - 101,942,500 = 0
    # Delta = [648 + sqrt(648**2 - 4*1.2*(-101,942,500))] / 2.4
    # Delta = [648 + sqrt(419,904 + 489,324,000)] / 2.4
    # Delta = [648 + 22,130] / 2.4 = 9,486
    
    return [0,0] # Placeholder

# Let's just calculate the values directly in the script
B = 10800 / 30
Delta = (648 + np.sqrt(648**2 - 4*1.2*(-101942500))) / 2.4
Dq = Delta / 10
print(f"B: {B}, Dq: {Dq}, Delta: {Delta}")
EOF
python3 solve_lf.py
