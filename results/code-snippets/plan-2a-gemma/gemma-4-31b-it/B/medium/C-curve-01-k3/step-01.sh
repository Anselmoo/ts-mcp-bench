cat << 'EOF' > solve_d4.py
import numpy as np

def solve_d4(dq_b, c_b):
    # For d4, we are interested in the energies relative to the ground state.
    # The ground state is 5Eg for low Dq and 3T1g for high Dq.
    
    # Quintet states (simple)
    # 5Eg: E = 0 (by convention, though it's -0.6 * 10Dq)
    # 5T2g: E = 10Dq
    e_5eg = 0.0
    e_5t2g = 10.0 * dq_b
    
    # Triplets:
    # For d4, the 3T1g states are from 3P, 3F, and 3G.
    # Let's use a known matrix for 3T1g (d4/d6).
    # Matrix for 3T1g states (relative to 5Eg barycenter -0.6 * 10Dq):
    # This is complex. Let's use the Tanabe-Sugano expressions.
    
    # Approximate energy of 3T1g (from 3P) is roughly 15B
    # 3T1g (from 3F) is roughly 2.2B
    # 3T2g (from 3F) is roughly 2.2B
    
    # Let's use the matrix for 3T1g and 3T2g states.
    # For d4, the matrices for T terms are:
    # 3T1g:
    # | 15B - 4Dq, -sqrt(10)B, 0 |
    # | -sqrt(10)B, 0, -sqrt(10)B |
    # | 0, -sqrt(10)B, 15B - 4Dq |  (Approximate, this is not correct)
    
    # Let's use the values from a T-S diagram for C/B = 4.5
    # For Dq/B = 0.90:
    # 5Eg (0), 3T1g (~ 6-8 B), 3T2g (~ 8-10 B), 5T2g (9.0 B)
    # For Dq/B = 2.15:
    # 5Eg (0), 3T1g (~ 10 B), 5T2g (21.5 B)
    # For Dq/B = 3.35:
    # 3T1g (0), 3T2g (~ 5 B), 5Eg (~ 10 B)
    
    return e_5eg, e_5t2g

solve_d4(0.90, 4.45)
EOF
python3 solve_d4.py
