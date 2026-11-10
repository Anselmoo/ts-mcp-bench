cat << 'EOF' > solution.py
import numpy as np
from itertools import combinations

def get_d_orbitals():
    # Orbitals: 0:z2, 1:x2-y2, 2:xy, 3:xz, 4:yz
    return np.arange(5)

def get_slater_determinants(n_elec=4):
    # Orbitals: 0-4 (spatial), 5-9 (spatial with spin down)
    # Total 10 spin-orbitals
    import itertools
    return list(itertools.combinations(range(10), n_elec))

def compute_ee_matrix(dets, B, C):
    # F0 is a constant shift, we can set it to 0 or ignore it
    # F2 = B, F4 = C - 2/3*B
    F2 = B
    F4 = C - (2/3)*B
    
    # Using the formulas for matrix elements of 1/r12 in d-orbitals
    # <m1 m2 | 1/r12 | m3 m4> = sum_{k=0,2,4} F_k * coeff(m1, m2, m3, m4, k)
    # For simplicity, we can use the known values for d-orbital repulsion.
    # Or use a simplified version for the specific symmetries.
    # Actually, it's better to use the matrices for the terms.
    # But for a general script, we can use the angular integrals.
    
    # Let's use a simplified matrix for d4 octahedral based on Racah parameters.
    # For d4, we can use the known energies of the free-ion terms and 
    # the splitting of those terms in an octahedral field.
    # This is the standard way to construct Tanabe-Sugano diagrams.
    pass

# Instead of building from scratch, I will use the standard formulas for d4.
# d4 High Spin ground state: 5Eg (t2g^3 eg^1)
# d4 Low Spin ground state: 1A1g (t2g^4)
# The 5D term splits into 5T2g and 5Eg.
# The 3H term splits into 3T1g, 3T2g, 3T1g, 3A2g.
# The 3F term splits into 3T1g, 3T2g, 3A2g.
# The 3P term splits into 3T1g.
# etc.

# To get precise values, I'll use a matrix diagonalization for each symmetry.
# The basis for each symmetry is the set of configurations that transform as that symmetry.

def solve_d4(dq_over_b, B, C):
    # d4 octahedral
    # High spin ground state: 5Eg (t2g^3 eg^1) and 5T2g (t2g^4) - wait, t2g^4 is not 5T2g.
    # t2g^3 eg^1 is 5Eg. t2g^4 is not possible for S=2.
    # For S=2, the only configurations are t2g^3 eg^1 (5Eg) and t2g^2 eg^2 (5T2g).
    # Energy of 5Eg = 6 Dq - 4 Dq = 2 Dq? No.
    # Energy relative to barycenter:
    # 5Eg: 3*(-4Dq) + 1*(6Dq) = -6Dq
    # 5T2g: 2*(-4Dq) + 2*(6Dq) = 4Dq
    # Wait, for d4 high spin, ground state is 5Eg.
    # E(5Eg) = -6 Dq, E(5T2g) = 4 Dq. Difference = 10 Dq.
    # But these are for S=2.
    
    # For S=1, we have more configurations:
    # t2g^4 (1A1g, 1T2g, 1Eg, 3T1g, 3T2g)
    # t2g^3 eg^1 (3T1g, 3T2g, 3A2g, 1T1g, 1T2g, 1Eg, 1A1g)
    # etc.
    
    # This is getting complex to implement from scratch. 
    # Let's use the known matrices for d4.
    # I will use a simplified set of equations for the lowest 6 levels.
    # Most of the lowest levels come from 5D, 3H, and 3F.
    
    # 5D: 5Eg (ground), 5T2g (10Dq)
    # 3H: 3T1g, 3T2g, etc.
    # 3F: 3T1g, 3T2g, etc.
    
    # For d4, the crossover from high-spin (5Eg) to low-spin (1A1g)
    # occurs at Dq/B approx 2.0 - 2.5.
    pass
EOF
