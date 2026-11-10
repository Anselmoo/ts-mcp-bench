cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt

def solve_d6(dq_b, c_b):
    # B = 1.0 (normalized)
    # Dq = dq_b
    # C = c_b
    dq = dq_b
    c = c_b
    
    # S=2
    e_s2 = np.array([-4*dq, 6*dq])
    
    # S=1
    # We use a simplified 3x3 matrix for the lowest triplet states
    # Based on T1g, T2g, and A2g
    # Matrix elements are approximations based on the T-S diagram
    # For d6, the triplets are T1g(F), T2g(F), A2g(F), T1g(P), T1g(H), T2g(H), Eg(H), A2g(H)
    # The lowest ones are T1g and T2g
    # Let's use a more accurate representation
    # S=1 matrix (6x6)
    # Basis: T1g(H), T2g(H), Eg(H), A2g(H), T1g(F), T2g(F), A2g(F), T1g(P)
    # This is too complex to implement.
    # Instead, let's use the known energies for d6 from a TS diagram.
    # For C/B = 4.557, the S=1 levels are approx:
    # E(3T1g) = -4*dq + 5*B + ...
    # E(3T2g) = -4*dq + 5*B + ...
    # E(3Eg) = -4*dq + 10*B + ...
    # E(3A2g) = -4*dq + 15*B + ...
    
    # Let's use the laPorte values for d6
    # S=1 levels (approx)
    e_s1 = np.array([
        -4*dq + 5*1.0, 
        -4*dq + 10*1.0,
        -4*dq + 15*1.0,
        -4*dq + 20*1.0,
        -4*dq + 25*1.0,
        -4*dq + 30*1.0
    ])
    
    # S=0
    # Lowest is 1A1g: E = -24*dq + E_rep
    # E_rep(1A1g) for d6 is approx 30*B + some C term
    # E_rep(1A1g) = 15B + 10C for d6? No.
    # For d6, E(1A1g) = -24*dq + (15B + 10C) (Wait, this is just a guess)
    # Let's use the actual formula for d6 1A1g:
    # E(1A1g) = -24*dq + (15B + some contribution from C)
    # For d6, the energy of 1A1g relative to 5T2g is:
    # E(1A1g) - E(5T2g) = -20*dq + (15B + 10C - 0) ? No.
    
    # Let's use the T-S diagram data for d6.
    # For C/B = 4.5, the transition 5T2g -> 1A1g occurs at Dq/B approx 2.0.
    # At Dq/B = 2.0, E(5T2g) = E(1A1g).
    # E(5T2g) = -4*dq.
    # -4*(2) = -24*(2) + E_rep => -8 = -48 + E_rep => E_rep = 40B.
    # So E(1A1g) = -24*dq + 40B.
    
    e_s0 = np.array([-24*dq + 40*1.0, -24*dq + 50*1.0, -24*dq + 60*1.0])
    
    all_levels = np.concatenate([e_s2, e_s1, e_s0])
    return all_levels

# This is too approximate. I need the actual matrices.
EOF
python3 solution.py
