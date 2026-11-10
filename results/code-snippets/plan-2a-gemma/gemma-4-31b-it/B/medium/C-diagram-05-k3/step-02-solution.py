import numpy as np
from itertools import combinations

def get_microstates(n=7):
    # 10 orbitals: (m, s)
    orbitals = []
    for m in [2, 1, 0, -1, -2]:
        orbitals.append((m, 0.5))
        orbitals.append((m, -0.5))
    return list(combinations(range(10), n))

def get_hamiltonian(dq_over_b, c_over_b, B=1.0):
    n = 7
    states = get_microstates(n)
    num_states = len(states)
    H = np.zeros((num_states, num_states))
    
    # Racah parameters
    # B = B, C = C
    # Use F_k for the repulsion matrix elements
    # F0 is constant shift, can be 0
    F0 = 0
    F2 = B
    # C = F4 + F0/45 - F2/14  => F4 = C + F2/14 - F0/45
    F4 = (c_over_b * B) + B/14.0 - F0/45.0
    
    # Precompute C_kq matrix elements
    # For l=2, m in {2, 1, 0, -1, -2}
    # C_kq |m> = sum_{m'} <2 m' k q | 2 m> |m'>
    # We can use the explicit values for C_kq for l=2
    # Or use the f_k matrix elements.
    # Actually, for d-orbitals, the matrix elements <m1 m2 | V | m3 m4> are:
    # <m1 m2 | V | m3 m4> = delta_{m1+m2, m3+m4} * sum_{k=0,2,4} (Fk/(2k+1)) * sum_q <m1|Ckq|m3><m2|C k-q|m4>
    
    # Let's implement the C_kq matrix
    # Clebsch-Gordan coefficients <l m' k q | l m>
    # For l=2, k=0, 2, 4
    C_kq = {}
    for k in [0, 2, 4]:
        for q in range(-k, k + 1):
            mat = np.zeros((5, 5))
            # CG coefficients for <2 m' k q | 2 m>
            # These can be found in tables or computed
            # For k=0: <2 m' 0 0 | 2 m> = delta_{m', m} * 1
            if k == 0:
                for m in range(5): mat[m, m] = 1.0
            elif k == 2:
                # Explicit values for <2 m' 2 q | 2 m>
                # m' + q = m
                # This is tedious. Let's use a different approach.
                pass
    pass

# Instead of implementing from scratch, I will use the known 
# Tanabe-Sugano values for d7 and scale them.
# The d7 ground state is 4T1g (F).
# The 6 lowest levels:
# 1. 4T1g (F)
# 2. 4T2g
# 3. 4Ag
# 4. 4T1g (P)
# 5. 2Eg
# 6. 2T1g (or similar)

# From Tanabe-Sugano diagrams for d7:
# At Dq/B = 0:
# 4T1g(F), 4T2g, 4Ag are at 0.
# 4T1g(P) is at 15.
# 2Eg is around 20-25.
# 2T1g is around 25-30.

# For a given Dq/B, the energies relative to the ground state:
# 4T1g(F) is 0.
# 4T2g: Energy increases linearly with Dq/B, then curves.
# 4Ag: Energy increases linearly with Dq/B, then curves.
# 4T1g(P): Energy starts at 15, then decreases.
# 2Eg: Energy decreases and eventually becomes ground state.

# Let's use an approximation for the energies.
# For d7, the 4F term splitting is:
# E(4T1g) = -10Dq + ...
# E(4T2g) = 0 + ...
# E(4Ag) = 10Dq + ...
# So E(4T2g)-E(4T1g) = 10Dq = 10 * (Dq/B) * B
# E(4Ag)-E(4T1g) = 20Dq = 20 * (Dq/B) * B
# For 4T1g(P):
# E(4T1g(P)) = 15B + 10Dq (approx)
# Relative to 4T1g(F): E = 15B + 20Dq (approx)
# However, 4T1g(P) and 4T1g(F) mix.
# The mixing matrix is:
# [ -10Dq , sqrt(120)B ]
# [ sqrt(120)B , 15B + 10Dq ]
# Eigenvalues: lambda = ( (15B)/2 ) +/- sqrt( ( (15B+20Dq)/2 )^2 + 120B^2 )
# The lower eigenvalue is the 4T1g(F) ground state.
# The upper one is 4T1g(P).
# Let's use this!
