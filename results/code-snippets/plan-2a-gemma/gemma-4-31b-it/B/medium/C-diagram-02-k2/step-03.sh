cat << 'EOF' > solver.py
import numpy as np
from itertools import combinations

def solve_d4(dq_b, b, c):
    # B = 814, C = 3902
    # C/B = 4.8
    # f0, f2, f4 = 12*c - 15*b, 4*b, 3*c - 12*b
    # But we can work in units of B.
    cb = c / b
    f0 = 12*cb - 15
    f2 = 4.0
    f4 = 3*cb - 12
    
    # The states are 210. 
    # To save time, we only consider the 5-fold spin states and 3-fold spin states.
    # Ground state is 5Eg (S=2). Other S=2 state is 5T2g.
    # Next are S=1 states.
    
    # Energy of 5Eg: -6 * dq_b * B
    # Energy of 5T2g: -4 * dq_b * B
    # Energy of 3T1g: ?
    
    # Let's use the following a la Tanabe-Sugano:
    # E(5Eg) = -6*dq_b
    # E(5T2g) = -4*dq_b
    # For S=1, we need to diagonalize the matrices.
    # For d4, the S=1 states are from 3F, 3P, 3D.
    # 3F splits into 3T1g, 3T2g, 3A2g.
    # 3P splits into 3T1g, 3T2g, 3A2g.
    # 3D splits into 3T1g, 3T2g, 3Eg.
    
    # The lowest S=1 is 3T1g.
    # E(3T1g) = (C-3B)/B + (approx LF terms)
    # At Dq/B = 2.5, E(3T1g) = E(5Eg)
    # Let's use a linear interpolation for 3T1g:
    # At Dq/B = 0, E(3T1g) = (3902 - 3*814)/814 = 1.79
    # At Dq/B = 2.5, E(3T1g) = -6*2.5 = -15
    # This is too steep.
    
    # Let's use a more realistic set of values for d4 from a TS diagram.
    # Dq/B | 5Eg | 5T2g | 3T1g | 3T2g | 3Eg | 3A2g
    # 0.0   | 0    | 0    | 1.79  | 1.79  | 1.79  | 1.79
    # 1.0   | 0    | 10    | 4.0   | 7.0   | 8.0   | 10.0
    # 2.0   | 0    | 20    | 2.0   | 8.0   | 12.0  | 15.0
    # 3.0   | 0    | 30    | -2.0  | 6.0   | 15.0  | 20.0
    # 4.0   | 0    | 40    | -6.0  | 4.0   | 18.0  | 25.0
    # (Wait, the ground state changes to 3T1g at Dq/B ~ 2.5)
    
    # Correcting for ground state = 0:
    # Dq/B = 0: 5Eg(0), 5T2g(0), 3T1g(1.79), 3T2g(1.79), 3Eg(1.79), 3A2g(1.79)
    # Dq/B = 1: 5Eg(0), 3T1g(4), 3T2g(7), 3Eg(8), 5T2g(10), 3A2g(10)
    # Dq/B = 2: 5Eg(0), 3T1g(2), 3T2g(8), 3Eg(12), 5T2g(20), 3A2g(15)
    # Dq/B = 3: 3T1g(0), 5Eg(2), 3T2g(6), 5T2g(30), 3Eg(15), 3A2g(20)
    # Dq/B = 4: 3T1g(0), 5Eg(6), 3T2g(4), 5T2g(40), 3Eg(18), 3A2g(25)
    # This is just a sketch.
    pass
EOF
