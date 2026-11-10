cat << 'EOF' > solver.py
import numpy as np
from itertools import combinations, product

def get_d4_energies(dq_b, b=1.0, c=4.0):
    # Orbitals: m = 2, 1, 0, -1, -2
    # Indices: 0, 1, 2, 3, 4
    # Octahedral field: t2g (1, 0, -1), eg (2, -2)
    # Let's use orbitals: 0:dxy, 1:dyz, 2:dzx, 3:dx2-y2, 4:dz2
    # t2g: 0, 1, 2. eg: 3, 4.
    # Energy of t2g = 0, Energy of eg = 10*dq_b * b
    
    # To simplify, we use the Racah parameters B and C.
    # We need the Coulomb matrix elements <i j | V | k l>.
    # For d-orbitals, these are tabulated.
    # We'll use the values for B=1, C=0 first and then adjust for C.
    # Actually, we can use the formula:
    # <m1 m2 | V | m3 m4> = sum_{k=0,2,4} G^k * ...
    # Let's use the matrix elements in terms of B and C.
    
    # Here's a simpler way: the energies of the states for d4.
    # We can use the secular equations for the mixing states.
    # For d4, the states that mix are the ones with the same symmetry and spin.
    # Spin-allowed: 5Eg and 5T2g.
    # Spin-forbidden: 3T1g, 3T2g, 3A2g, 1T2g, 1E, 1A1g.
    
    # Let's use the approximation:
    # E(5T2g) = 10 * dq_b
    # For the 3T1g states:
    # There are three 3T1g states: 3T1g(P), 3T1g(F), 3T1g(H).
    # Their free-ion energies are:
    # E(3P) = 15*B + 3*C (Wait, check this)
    # E(3F) = 15*B - C
    # E(3H) = 15*B - 3*C
    # This is relative to some baseline.
    
    # Let's use the values from a reliable TS diagram for d4:
    # For d4:
    # 5Eg is ground state.
    # 5T2g is at 10Dq.
    # 3T1g is the lowest spin-forbidden.
    # For Dq/B = 0.9, E(3T1g)/B is approx 14.
    # For Dq/B = 2.15, E(3T1g)/B is approx 10.
    # For Dq/B = 3.35, the ground state is 3T1g.
    
    # Let's use the actual matrix for d4.
    # The basis states for d4 are combinations of (m1, m2, m3, m4) with spin.
    # Total states = 10C4 = 210.
    # This is manageable.
    
    def get_coulomb_matrix():
        # Matrix elements for d-orbitals in terms of B and C
        # <m1 m2 | V | m3 m4>
        # Using the formulas from a reliable source.
        # m = 2, 1, 0, -1, -2
        # This is tedious to implement.
        pass

EOF
