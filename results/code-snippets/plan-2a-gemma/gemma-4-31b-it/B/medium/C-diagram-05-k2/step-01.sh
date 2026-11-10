cat << 'EOF' > solution.py
import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import eigh
from sympy.physics.wigner import wigner_3j

def get_gaunt_matrix(l, k):
    """Compute the matrix elements <l, m | C_q^{(k)} | l, m'>."""
    matrix = {}
    for m in range(-l, l + 1):
        for m_prime in range(-l, l + 1):
            q = m - m_prime
            if abs(q) <= k:
                # The formula for the Gaunt coefficient for d-orbitals
                # is slightly different depending on normalization.
                # We use the 3j symbol as the primary part.
                val = wigner_3j(l, k, l, -m, q, m_prime)
                matrix[(m, m_prime, q)] = float(val)
    return matrix

def compute_energies(B, C, dq_over_b):
    # Racah parameters to F_k
    # B = (F2 + F4)/14
    # C = (F2 - 5F4)/4
    # F4 = (14*B - 4*C)/(-6) = (4*C - 14*B)/6 = (2*C - 7*B)/3
    # F2 = 14*B - F4 = 14*B - (2*C - 7*B)/3 = (42*B - 2*C + 7*B)/3 = (49*B - 2*C)/3
    F4 = (2*C - 7*B) / 3.0
    F2 = (49*B - 2*C) / 3.0
    F0 = 0.0 # Constant shift
    
    l = 2
    gaunt = get_gaunt_matrix(l, 2)
    gaunt4 = get_gaunt_matrix(l, 4)
    gaunt0 = get_gaunt_matrix(l, 0)
    
    # Orbitals: m = 2, 1, 0, -1, -2
    # Octahedral splitting:
    # t2g: m = 1, 0, -1 (approx) -> -4Dq
    # eg: m = 2, -2 (approx) -> 6Dq
    # A better way: t2g (xy, xz, yz), eg (z2, x2-y2)
    # The m-basis is not the best for Oh, but we can use the real orbitals.
    # However, we can use the m-basis and the Oh Hamiltonian.
    # H_LF = sum_i eps_i n_i
    # For d7, ground state is high spin.
    # For S=3/2, 4 up, 3 down.
    # Up electrons: fill all 5 orbitals.
    # Down electrons: occupy 3 out of 5 orbitals.
    # This is equivalent to d3 electrons in the down spin!
    # Let's calculate for d3 and then relate.
    
    # Wait, the d7 high spin is 4 up, 3 down.
    # Up spin: 4 electrons in 5 orbitals.
    # Down spin: 3 electrons in 5 orbitals.
    # The total energy is E = E_up + E_down + E_up_down.
    # E_up_down = sum_{i_up, j_down} <i_up j_down | H_ee | i_up j_down>
    # This is getting complex. Let's use the simpler d3 result for the 4F and 4P terms.
    
    # Standard TS energies for d3/d7 high spin:
    # E(^4A2g) = -12Dq
    # E(^4T2g) = -4Dq
    # E(^4T1g(F, P)): roots of the 2x2 matrix
    # H = [[-4Dq, 6B*sqrt(2)], [6B*sqrt(2), 15B - 4Dq]]
    
    Dq = dq_over_b * B
    
    # 4F terms
    e_a2g = -12 * Dq
    e_t2g = -4 * Dq
    
    # 4T1g terms
    h_t1 = np.array([[-4 * Dq, 6 * B * np.sqrt(2)],
                     [6 * B * np.sqrt(2), 15 * B - 4 * Dq]])
    e_t1 = np.linalg.eigvalsh(h_t1)
    
    # The barycenter of 4F is 0.
    # For d3: ground is A2g. E_rel = E - e_a2g.
    # For d7: ground is T1g. E_rel = E - min(e_t1).
    
    # The d7 high spin levels are:
    # T1g(F), T2g(F), A2g(F), T1g(P)
    # But wait, the T1g(F) and T1g(P) are the eigenvalues of the matrix.
    
    levels = []
    levels.append(("^4T_{1g}", e_t1[0]))
    levels.append(("^4T_{2g}", e_t2g))
    levels.append(("^4A_{2g}", e_a2g))
    levels.append(("^4T_{1g}", e_t1[1]))
    
    # Now we need doublets for the 6 lowest.
    # The doublets are generally higher in energy.
    # For d3/d7, the lowest doublets are from 2H and 2G.
    # For simplicity, let's focus on the quartets first.
    
    # To get the doublets, we would need the full matrix.
    # Since we need 6 levels, and we have 4 quartets, 
    # we need 2 doublets.
    # The lowest doublets for d7 are typically ^2E_g and ^2T_{1g}.
    # These are hard to compute without the full matrix.
    # Let's approximate the doublet energies as being above the quartets.
    # Or use a known TS diagram for d7.
    
    # From a standard d7 TS diagram:
    # High spin: ^4T1g < ^4T2g < ^4A2g < ^4T1g(P)
    # Low spin: ^2E_g is the ground state for large Dq/B.
    # Transition is around Dq/B = 2.
    
    return levels

# Let's refine the code to use a more complete model.
EOF
python3 solution.py
