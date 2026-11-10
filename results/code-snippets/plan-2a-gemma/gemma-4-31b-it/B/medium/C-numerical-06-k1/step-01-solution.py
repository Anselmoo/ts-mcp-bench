import numpy as np
from scipy.optimize import fsolve

def energy_calc(params):
    Dq, B = params
    Delta = 10 * Dq
    
    # For d7 high spin, the states are 4T1g(F), 4T2g, 4A2g, 4T1g(P)
    # E(4T2g) = 0.5 * Delta
    # E(4A2g) = 1.5 * Delta + 6*B
    # T1g states are eigenvalues of:
    # [[-0.5*Delta, 6*B], [6*B, 15*B - 0.5*Delta]]
    # Wait, is the off-diagonal 6B? Let's use the standard T-S matrix.
    # For d2/d7, the interaction is between T1g(F) and T1g(P).
    # The matrix elements are:
    # H11 = -0.5*Delta
    # H22 = 15*B - 0.5*Delta
    # H12 = 6*B
    # No, H12 = 6*B is for a different basis.
    
    # Let's use the roots of the cubic equation for 4F splitting and the 4P state.
    # For d7 high spin, the transitions are:
    # v1: 4T1g(F) -> 4T2g
    # v2: 4T1g(F) -> 4A2g
    # v3: 4T1g(F) -> 4T1g(P)
    
    # Correct Matrix for T1g states (from Tanabe-Sugano):
    # The two T1g states are roots of:
    # lambda^2 - (15B - Delta) lambda - (15B*Delta - 0.75*Delta^2) = 0? No.
    
    # Let's use the most reliable forms for d7 high spin:
    # E(4T2g) = 0.5 * Delta
    # E(4A2g) = 1.5 * Delta + 6*B
    # E(4T1g) are roots of:
    # x^2 - (15*B - Delta)*x - (15*B*Delta - 0.75*Delta^2) = 0 ? No.
    
    # Actually, let's use the property:
    # v2 - v1 = E(4A2g) - E(4T2g) = Delta + 6*B
    # v3 = E(4T1g(P)) - E(4T1g(F))
    # v1 = E(4T2g) - E(4T1g(F))
    
    # For the T1g states, the eigenvalues of [[-0.5*Delta, 6*B], [6*B, 15*B - 0.5*Delta]] are:
    # L = 0.5 * (15*B - Delta +/- sqrt( (15*B)^2 + 144*B^2 ))
    # This sqrt(369*B^2) is 19.2*B.
    # So E(4T1g(F)) = 0.5*(15*B - Delta - 19.2*B) = -2.1*B - 0.5*Delta
    # E(4T1g(P)) = 0.5*(15*B - Delta + 19.2*B) = 17.1*B - 0.5*Delta
    
    # Let's try this:
    # v1 = 0.5*Delta - (-2.1*B - 0.5*Delta) = Delta + 2.1*B
    # v2 = (1.5*Delta + 6*B) - (-2.1*B - 0.5*Delta) = 2*Delta + 8.1*B
    # v3 = (17.1*B - 0.5*Delta) - (-2.1*B - 0.5*Delta) = 19.2*B
    
    # But v2 - v1 = Delta + 6*B.
    # Let's check: (2*Delta + 8.1*B) - (Delta + 2.1*B) = Delta + 6*B. Matches!
    
    # Now let's check v3: v3 = 19.2*B.
    # Given v3 = 20320, B = 20320 / 19.2 = 1058.
    # Given v2 - v1 = 19550 - 9180 = 10370.
    # Delta + 6*B = 10370 => Delta = 10370 - 6(1058) = 10370 - 6348 = 4022.
    # Then v1 = Delta + 2.1*B = 4022 + 2.1(1058) = 4022 + 2221 = 6243.
    # But v1 = 9180.
    
    # The interaction element might be different.
    # The correct matrix for d2/d7 T1g states is:
    # H = [[-0.5*Delta, 6*B], [6*B, 15*B - 0.5*Delta]] ? 
    # No, it's [[-0.5*Delta, 6*B], [6*B, 15*B - 0.5*Delta]] only if we use a specific basis.
    # The off-diagonal element is actually 6*B.
    # Let me double check the energy of 4T2g.
    # E(4T2g) = 0.5 * Delta.
    # E(4A2g) = 1.5 * Delta + 6*B.
    # Let's use the roots of the secular equation for 4F:
    # x^3 + 2*Delta*x^2 - (10*Dq^2 + 15*B^2)*x ... no.
    
    # Let's use a different approach.
    # For d7 high spin:
    # v1 = 8*Dq (approx)
    # v2 = 18*Dq (approx)
    # v3 = 15*B + 10*Dq (approx)
    # v2/v1 = 19550 / 9180 = 2.13
    # 18/8 = 2.25.
    # If 10Dq = 10370 (v2-v1), then Dq = 1037.
    # v1 = 8*Dq = 8296 (close to 9180)
    # v3 = 15*B + 10370 = 20320 => 15*B = 9950 => B = 663.
    
    # Let's use a more precise model.
    # For d7, the energies of the 4F states are:
    # E(4T2g) = 0.5*Delta
    # E(4A2g) = 1.5*Delta + 6*B
    # E(4T1g(F)) = -0.5*Delta + (some correction)
    # The correction comes from mixing with 4T1g(P).
    # The two T1g states are roots of:
    # (E + 0.5*Delta)(E - 15*B + 0.5*Delta) - (6*B)^2 = 0
    # E^2 - (15*B - Delta)E + (0.5*Delta)(0.5*Delta - 15*B) - 36*B^2 = 0
    # E^2 - (15*B - Delta)E + 0.25*Delta^2 - 7.5*B*Delta - 36*B^2 = 0
    
    # Let's use this in the script to find Dq and B.
    return 0

def solve_system():
    v1 = 9180
    v2 = 19550
    v3 = 20320
    
    # Try a range of B and Dq
    best_err = float('inf')
    best_params = (0, 0)
    
    for B in np.linspace(400, 1200, 1000):
        for Dq in np.linspace(500, 1500, 1000):
            Delta = 10 * Dq
            # T1g roots
            # E^2 - (15*B - Delta)E + 0.25*Delta^2 - 7.5*B*Delta - 36*B^2 = 0
            a = 1
            b = -(15*B - Delta)
            c = 0.25*Delta**2 - 7.5*B*Delta - 36*B**2
            
            disc = b**2 - 4*a*c
            if disc < 0: continue
            sqrt_disc = np.sqrt(disc)
            e_t1g_f = ( -b - sqrt_disc ) / 2
            e_t1g_p = ( -b + sqrt_disc ) / 2
            e_t2g = 0.5 * Delta
            e_a2g = 1.5 * Delta + 6*B
            
            calc_v1 = e_t2g - e_t1g_f
            calc_v2 = e_a2g - e_t1g_f
            calc_v3 = e_t1g_p - e_t1g_f
            
            err = (calc_v1 - v1)**2 + (calc_v2 - v2)**2 + (calc_v3 - v3)**2
            if err < best_err:
                best_err = err
                best_params = (Dq, B)
    return best_params

print(solve_system())
