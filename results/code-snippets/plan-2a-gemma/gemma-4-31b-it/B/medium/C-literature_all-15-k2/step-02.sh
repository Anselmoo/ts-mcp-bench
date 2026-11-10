cat << 'EOF' > solver.py
import numpy as np
from scipy.optimize import fsolve

def equations(p):
    B, Dq = p
    Delta_o = 10 * Dq
    
    # d7 high spin energies relative to barycenter of F term
    # E(4A2g) = 6*Delta_o - 15*B
    # E(4T2g) = 5*Delta_o - 15*B
    # E(4T1g) are eigenvalues of [[ 4*Delta_o - 15*B, 6*B ], [ 6*B, 15*B ]] - this was d3
    # Let's use the correct d7 matrix from a reliable source.
    # For d7, the F term is T1g, T2g, A2g.
    # The energies relative to the barycenter:
    # E(4A2g) = 6*Delta_o - 15*B (Wait, this can't be right)
    
    # Let's use the d3 formulas and invert them.
    # For d3: E(4A2g)=0, E(4T2g)=Delta_o, E(4T1g) = matrix [[4*Delta_o-15*B, 6*B],[6*B, 15*B]]
    # For d7, the ground state is the lowest T1g state.
    # The transition energies are:
    # nu1 = E(4T2g) - E(4T1g_low)
    # nu2 = E(4A2g) - E(4T1g_low)
    # nu3 = E(4T1g_high) - E(4T1g_low)
    
    # In d3, E(4T1g_high) - E(4T1g_low) = sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
    # And E(4T1g_low) = (4*Delta_o) / 2 - 0.5 * sqrt(...) = 2*Delta_o - 0.5 * sqrt(...)
    # E(4T2g) = Delta_o
    # E(4A2g) = 0
    # But this is relative to 4A2g. For d7, we need the energies relative to the ground state.
    # The ground state is 4T1g_low.
    # So E(4T1g_low) = 0.
    # Then E(4T1g_high) = sqrt((4*Delta_o - 30*B)**2 + 144*B**2) = nu3
    # E(4T2g) = Delta_o - (2*Delta_o - 0.5 * sqrt(...)) = -Delta_o + 0.5 * nu3 = nu1
    # E(4A2g) = 0 - (2*Delta_o - 0.5 * sqrt(...)) = -2*Delta_o + 0.5 * nu3 = nu2
    
    # Let's check these:
    # nu2 - nu1 = (-2*Delta_o + 0.5*nu3) - (-Delta_o + 0.5*nu3) = -Delta_o.
    # But nu2 - nu1 = 16305 - 8480 = +7825.
    # This means the signs of Delta_o are different.
    # Let's use E(4T2g) = 3*Delta_o and E(4A2g) = 4*Delta_o relative to some origin.
    # Let's try:
    # nu1 = E(4T2g) - E(4T1g_low)
    # nu2 = E(4A2g) - E(4T1g_low)
    # This implies nu2 - nu1 = E(4A2g) - E(4T2g) = Delta_o.
    # Now we just need nu1 and nu3.
    # nu3 = sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
    # nu1 = E(4T2g) - E(4T1g_low).
    # For d7, E(4T2g) relative to the barycenter is 5*Delta_o - 15*B.
    # E(4T1g_low) relative to the barycenter is 2*Delta_o - 0.5 * nu3.
    # So nu1 = (5*Delta_o - 15*B) - (2*Delta_o - 0.5 * nu3) = 3*Delta_o - 15*B + 0.5 * nu3.
    
    nu3_calc = np.sqrt((4*Delta_o - 30*B)**2 + 144*B**2)
    nu1_calc = 3*Delta_o - 15*B + 0.5 * nu3_calc
    nu2_calc = 4*Delta_o - 15*B + 0.5 * nu3_calc
    
    return [nu1_calc - 8480, nu3_calc - 20360]

B_guess, Dq_guess = 700, 700
sol = fsolve(equations, [B_guess, Dq_guess])
print(f"B = {sol[0]:.2f}, Dq = {sol[1]:.2f}")
EOF
python3 solver.py
