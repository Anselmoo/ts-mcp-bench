import numpy as np
from itertools import combinations
from sympy import symbols, FloatingPoint
from sympy.physics.quantum.cg import CG

def get_cg(l1, m1, l2, m2, l3, m3):
    try:
        return float(CG(l1, m1, l2, m2, l3, m3).doit())
    except:
        return 0.0

def get_angular_factor(m1, m2, m3, m4, k):
    # <m1 m2 | k | m3 m4> = sum_q <l m1 k q l m3> * <l m2 k -q l m4> * (-1)^(k-q)
    # This is for the Coulomb integral.
    # For d orbitals, l=2.
    l = 2
    factor = 0.0
    for q in range(-k, k + 1):
        # CG(l1, m1, l2, m2, l3, m3)
        # We need <l m1 k q l m3> which is the CG coefficient for adding l and k to get l
        # But the notation is <l m1 k q | l m3>
        # In sympy.physics.quantum.cg, CG(l1, m1, l2, m2, l3, m3) is <l1 m1 l2 m2 | l3 m3>
        # So we need CG(l, m1, k, q, l, m3) - No, the indices are different.
        # The correct CG is <l m3 k q | l m1>
        term = get_cg(l, m3, k, q, l, m1) * get_cg(l, m4, k, -q, l, m2)
        if (k - q) % 2 == 1:
            factor -= term
        else:
            factor += term
    return factor

# Precompute the angular factors for k=0, 2, 4
m_vals = [2, 1, 0, -1, -2]
angular_factors = {}
for m1 in m_vals:
    for m2 in m_vals:
        for m3 in m_vals:
            for m4 in m_vals:
                factors = []
                for k in [0, 2, 4]:
                    factors.append(get_angular_factor(m1, m2, m3, m4, k))
                angular_factors[(m1, m2, m3, m4)] = factors

def solve(dq_over_b, b, c):
    # C/B = (F4 + 1/4 F2) / (F2 - 1/4 F4)
    # F2 = B + 1/4 F4
    # C = F4 + 1/4(B + 1/4 F4) = F4 + 1/4 B + 1/16 F4 = 17/16 F4 + 1/4 B
    # 17/16 F4 = C - 1/4 B  => F4 = (16/17) * (C - 1/4 B) = (16 C - 4 B) / 17
    # F2 = B + (4 C - B) / 17 = (17 B + 4 C - B) / 17 = (16 B + 4 C) / 17
    # F0 is not needed for the energy relative to the ground state if we subtract it.
    
    f4 = (16 * c - 4 * b) / 17.0
    f2 = (16 * b + 4 * c) / 17.0
    f0 = 0 # Reference
    f_vals = [f0, f2, f4]
    
    # Basis states: combinations of 5 electrons in 10 orbitals
    # Orbitals: (m, spin), m in [2, 1, 0, -1, -2], spin in [1, -1]
    orbitals = []
    for m in m_vals:
        orbitals.append((m, 1))
        orbitals.append((m, -1))
    
    basis = list(combinations(range(10), 5))
    n_states = len(basis)
    hamiltonian = np.zeros((n_states, n_states))
    
    # Orbital energies (LF)
    # d_xy, d_yz, d_xz (t2g) -> -4Dq
    # d_z2, d_x2-y2 (eg) -> +6Dq
    # Map m to orbital type:
    # m=2: d_x2-y2 (eg)
    # m=-2: d_x2-y2 (eg)
    # m=0: d_z2 (eg)
    # m=1: d_xz, d_yz (t2g)
    # m=-1: d_xz, d_yz (t2g)
    # Wait, let's use a proper mapping:
    # t2g: m=1, -1, 0 (Wait, d_xy, d_yz, d_xz are usually combined m's)
    # Standard mapping:
    # t2g: d_xy (m=2,-2), d_xz (m=1,-1), d_yz (m=1,-1) - No.
    # Let's use: 
    # d_z2: m=0
    # d_x2-y2: m=2, -2
    # d_xy: m=2, -2
    # d_xz: m=1, -1
    # d_yz: m=1, -1
    # This is confusing. Let's use:
    # Orbital index 0, 1, 2: t2g
    # Orbital index 3, 4: eg
    # Then we need to map these to m_l values for the Coulomb integrals.
    # t2g: m=1, -1, 0 (Wait, this depends on the axes).
    # Let's use:
    # t2g: m=1, m=-1, m=0 (but a specific combination)
    # Actually, the simplest is:
    # t2g orbitals: d_xy, d_yz, d_xz
    # eg orbitals: d_z2, d_x2-y2
    # We can represent these as linear combinations of m_l states.
    # d_z2 = |0>
    # d_x2-y2 = 1/sqrt(2) (|2> + |-2>)
    # d_xy = i/sqrt(2) (|2> - |-2>)
    # d_xz = -1/sqrt(2) (|1> + |-1>)
    # d_yz = 1/sqrt(2) (|1> - |-1>)
    # Then we compute the matrix elements <ab|V|cd> in this basis.
    
    # This is getting complex. Let's use the simplified energies for d5.
    # For d5, the terms are 6A1g, 4T1g(G), 4T2g(G), 4Eg(G), 4T1g(P), 2T2g, 2T1g, 2Eg.
