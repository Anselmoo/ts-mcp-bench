cat << 'EOF' > solve_dq_b.py
import numpy as np
from scipy.optimize import fsolve

def get_energies(Dq, B):
    # For d3 (which is the hole analogue of d7)
    # E(A2g) = 0
    # E(T2g) = 10 * Dq
    # E(T1g_F) and E(T1g_P) are roots of the quadratic
    # Matrix for T1g:
    # [[-12*Dq + 15*B, 6*sqrt(10)*Dq],
    #  [6*sqrt(10)*Dq, -12*Dq + 15*B + 12*Dq]]
    # Wait, these are relative to the barycenter.
    
    # Barycenter energies:
    e_a2g = -12 * Dq
    e_t2g = -4 * Dq
    
    # Matrix for T1g states:
    # The states are |T1g(F)> and |T1g(P)>
    # H = [[-12*Dq + 15*B, 6*sqrt(10)*Dq],
    #      [6*sqrt(10)*Dq, -12*Dq + 15*B + 12*Dq]]
    # No, this matrix is for d3.
    
    # Let's use the standard formula:
    # E(T1g) = 0.5 * (-12*Dq + 15*B +/- sqrt((12*Dq - 15*B)**2 + 120*Dq**2))
    term = np.sqrt((12*Dq - 15*B)**2 + 120*Dq**2)
    e_t1g_f = 0.5 * (-12*Dq + 15*B - term)
    e_t1g_p = 0.5 * (-12*Dq + 15*B + term)
    
    return e_a2g, e_t2g, e_t1g_f, e_t1g_p

def equations(vars):
    Dq, B = vars
    e_a2g, e_t2g, e_t1g_f, e_t1g_p = get_energies(Dq, B)
    
    # For d7 high spin, the ground state is T1g(F).
    # The transitions are:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    
    v1 = e_t2g - e_t1g_f
    v2 = e_a2g - e_t1g_f
    v3 = e_t1g_p - e_t1g_f
    
    # We have 3 equations and 2 variables.
    # We use v1 and v3 to solve for Dq and B, then check v2.
    # But let's use a least-squares approach or just v1 and v2.
    
    # Target values: 9180, 19550, 20320
    # Wait, let's check if this state order is correct.
    # e_t1g_f is the most negative.
    # Then e_t2g is -4*Dq.
    # Then e_a2g is -12*Dq.
    # Wait, -12*Dq is more negative than -4*Dq.
    # So e_a2g < e_t2g.
    # And e_t1g_f < e_a2g < e_t2g < e_t1g_p?
    # Let's check with an example: Dq=1000, B=600
    # e_a2g = -12000
    # e_t2g = -4000
    # term = sqrt((12000-9000)**2 + 120*1000^2) = sqrt(3000^2 + 120*10^6) = sqrt(9*10^6 + 120*10^6) = 11357
    # e_t1g_f = 0.5 * (-12000 + 9000 - 11357) = -7178
    # e_t1g_p = 0.5 * (-12000 + 9000 + 11357) = 4178
    # Order: e_a2g(-12000) < e_t1g_f(-7178) < e_t2g(-4000) < e_t1g_p(4178)
    # In this case, e_a2g is the ground state. This is d3.
    # For d7, the ground state is e_t1g_f? No, the ground state is the hole analogue.
    # The energies for d7 are E(d7) = -E(d3) + constant.
    # So the order for d7 is:
    # -e_t1g_p < -e_t2g < -e_t1g_f < -e_a2g
    # Let's test: -4178 < 4000 < 7178 < 12000
    # Ground state: -e_t1g_p? No, that's not right.
    # Let's use the TS diagram for d7.
    # Ground state: T1g. 
    # 1st excited: T2g.
    # 2nd excited: A2g.
    # 3rd excited: T1g(P).
    # This means:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # Let's find E(T1g_F), E(T2g), E(A2g), E(T1g_P) for d7.
    # E(d7, state) = -E(d3, state)
    # E(d7, A2g) = -(-12*Dq) = 12*Dq
    # E(d7, T2g) = -(-4*Dq) = 4*Dq
    # E(d7, T1g_F) = -e_t1g_f_d3
    # E(d7, T1g_P) = -e_t1g_p_d3? No, T1g(P) should stay high.
    
    # Actually, the simplest way is:
    # For d7, the energies relative to T1g(F) are:
    # v1 = E(T2g) - E(T1g_F)
    # v2 = E(A2g) - E(T1g_F)
    # v3 = E(T1g_P) - E(T1g_F)
    # And we know that:
    # E(A2g) - E(T2g) = E(d7, A2g) - E(d7, T2g) = 12*Dq - 4*Dq = 8*Dq.
    # So v2 - v1 = 8*Dq.
    # Also v3 = E(T1g_P) - E(T1g_F).
    # From d3, E(T1g_P) - E(T1g_F) = term = sqrt((12*Dq - 15*B)**2 + 120*Dq**2).
    # So v3 = sqrt((12*Dq - 15*B)**2 + 120*Dq**2).
    # And v1 = E(T2g) - E(T1g_F) = 4*Dq - (-e_t1g_f_d3)? No.
    # Let's use: E(d7, T2g) = 4*Dq, E(d7, T1g_F) = -e_t1g_f_d3 = -0.5*(-12*Dq + 15*B - term).
    # v1 = 4*Dq + 0.5*(-12*Dq + 15*B - term) = 4*Dq - 6*Dq + 7.5*B - 0.5*term = -2*Dq + 7.5*B - 0.5*term.
    # Let's check this.
    
    v1 = -2*Dq + 7.5*B - 0.5*term
    v2 = v1 + 8*Dq = 6*Dq + 7.5*B - 0.5*term
    v3 = term
    
    return [v1 - 9180, v2 - 19550, v3 - 20320]

# We have 3 equations, but only 2 variables. 
# Let's use v2 - v1 = 8*Dq to find Dq.
# v2 - v1 = 19550 - 9180 = 10370
# 8*Dq = 10370  =>  Dq = 10370 / 8 = 1296.25
# Then we use v3 = 20320 to find B.
# v3**2 = (12*Dq - 15*B)**2 + 120*Dq**2
# 20320**2 = (12*1296.25 - 15*B)**2 + 120 * 1296.25**2
# 412902400 = (15555 - 15*B)**2 + 120 * 1680264.0625
# 412902400 = (15555 - 15*B)**2 + 201631687.5
# (15555 - 15*B)**2 = 412902400 - 201631687.5 = 211270712.5
# 15555 - 15*B = +/- sqrt(211270712.5) = +/- 14535.15
# Case 1: 15*B = 15555 - 14535.15 = 1019.85  =>  B = 67.99
# Case 2: 15*B = 15555 + 14535.15 = 30090.15  =>  B = 2006.01
# Now check v1 = -2*Dq + 7.5*B - 0.5*v3 = 9180
# Case 1: v1 = -2*1296.25 + 7.5*67.99 - 0.5*20320 = -2592.5 + 509.9 - 10160 = -12242.6 (Wrong)
# Case 2: v1 = -2*1296.25 + 7.5*2006.01 - 0.5*20320 = -2592.5 + 15045.1 - 10160 = 2292.6 (Wrong)
# Something is wrong. Let me re-check the v1 formula.
EOF
python3 solve_dq_b.py
