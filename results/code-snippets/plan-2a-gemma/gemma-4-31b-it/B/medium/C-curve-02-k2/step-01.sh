cat << 'EOF' > d3_energies.py
import numpy as np
from itertools import combinations

def solve_d3(dq_over_b, c_over_b):
    # Racah parameters: B=1, C=c_over_b
    B = 1.0
    C = c_over_b
    Dq = dq_over_b * B
    
    # Orbitals: 0: dxy, 1: dxz, 2: dyz, 3: dz2, 4: dx2-y2
    # Energy of orbitals in Oh field:
    # t2g: -4 Dq, eg: 6 Dq
    orbital_energies = np.array([-4*Dq, -4*Dq, -4*Dq, 6*Dq, 6*Dq])
    
    # We need the repulsion matrix elements for d3.
    # Since we want the lowest excited states, we can focus on the 
    # most important configurations: t2g^3, t2g^2 eg^1, t2g^1 eg^2.
    # But it's safer to use the full d3 basis.
    # Total states = 10C3 = 120.
    # However, the terms split into multiplets.
    # We can use the symmetry of the Oh group to block-diagonalize.
    
    # To simplify, let's use the known results for d3 Oh.
    # The ground state is 4A2g.
    # The excited states are 4T2g, 4T1g(F), 4T1g(P), and doublets.
    
    # 4A2g: configuration t2g^3. Energy = 3*(-4*Dq) + repulsion
    # 4T2g: configuration t2g^2 eg^1. Energy = 2*(-4*Dq) + 6*Dq + repulsion
    # 4T1g(F) and 4T1g(P): mixing.
    
    # For d3:
    # E(4A2g) = 0 (ground state, by convention)
    # E(4T2g) = 10 Dq
    # E(4T1g) is solved from the 2x2 matrix for 4T1g(F) and 4T1g(P).
    # Matrix:
    # [ 18 Dq - 6 B,  6 B ]
    # [ 6 B,          15 B - 18 Dq ]
    # Wait, these are relative to the 4F barycenter? 
    # Let's use the Tanabe-Sugano values or the formula from a textbook.
    # For d3:
    # E(4A2g) = 0
    # E(4T2g) = 10 Dq
    # E(4T1g_1), E(4T1g_2) are eigenvalues of:
    # [ 18 Dq - 6 B, 6 B ]
    # [ 6 B, 15 B - 18 Dq ]
    # No, that's not quite right.
    
    # Let's use the energies relative to the ground state 4A2g.
    # E(4T2g) = 10 Dq
    # For the 4T1g terms, the matrix is:
    # [ 18 Dq - 6 B, 6 B ]
    # [ 6 B, 15 B - 18 Dq ] 
    # Wait, this matrix is for the energies relative to the center of gravity of 4F?
    # Let's re-check. 
    # For d3, the 4F term splits into A2g, T2g, T1g(F).
    # E(A2g) = 0, E(T2g) = 10 Dq, E(T1g(F)) = 12 Dq - 6 B (approx).
    
    # Actually, let's use the formula from a reliable source:
    # For d3, the energy of 4A2g is the reference (0).
    # E(4T2g) = 10 Dq
    # The two 4T1g states are the roots of:
    # E^2 - E(18 Dq - 6 B + 15 B - 18 Dq) + (18 Dq - 6 B)(15 B - 18 Dq) - (6 B)^2 = 0
    # E^2 - E(9 B) + (18 Dq - 6 B)(15 B - 18 Dq) - 36 B^2 = 0
    # E = [ 9 B +/- sqrt( 81 B^2 - 4((18 Dq - 6 B)(15 B - 18 Dq) - 36 B^2) ) ] / 2
    # E = [ 9 B +/- sqrt( 81 B^2 - 4(270 Dq B - 324 Dq^2 - 90 B^2 + 108 Dq B - 36 B^2) ) ] / 2
    # E = [ 9 B +/- sqrt( 81 B^2 - 4(-324 Dq^2 + 378 Dq B - 126 B^2) ) ] / 2
    # E = [ 9 B +/- sqrt( 1296 Dq^2 - 1512 Dq B + 585 B^2 ) ] / 2
    
    # Let's check for the doublets.
    # For d3, the lowest doublet is 2E_g or 2T_1g.
    # In the TS diagram for d3, the 2E_g state is below 4T2g for some Dq/B.
    # Let's use the approximated energy of the 2Eg state.
    # From various sources, for d3, the lowest doublet 2Eg has energy:
    # E(2Eg) = -1.5 B + 0.5 C + 3 Dq (relative to 4F)
    # But 4A2g is at -30 Dq (relative to 4F barycenter)? No.
    # Let's be careful.
    
    # Let's use a more robust way: find the values from the Tanabe-Sugano diagram for d3.
    # Ground: 4A2g
    # Excited: 4T2g, 4T1g(F), 4T1g(P), 2E_g, 2T_1g...
    # Looking at d3 TS diagram:
    # The lowest excited states are 4T2g and 2Eg.
    # At Dq/B = 1.0: 4T2g is around 10, 2Eg is around 12-15.
    # At Dq/B = 2.2: 4T2g is 22, 2Eg is around 15-20.
    # At Dq/B = 3.5: 4T2g is 35, 2Eg is lower.
    
    # Actually, I should use the full calculation for d3. 
    # Let's use the Racah matrix for d3.
EOF
python3 d3_energies.py
