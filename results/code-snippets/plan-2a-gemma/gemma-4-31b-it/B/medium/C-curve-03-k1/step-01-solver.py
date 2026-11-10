import numpy as np

def solve_d7(dq_over_b):
    # B = 1.0
    dq = dq_over_b
    delta = 10 * dq
    
    # Quartets: relative to 4A2g
    # Matrix for 4T1g
    h_t1g = np.array([[-1.5 * delta, 6.0],
                      [6.0, -1.5 * delta + 15.0]])
    eigvals_t1g = np.linalg.eigvalsh(h_t1g)
    
    # 4T2g energy
    e_t2g = -delta
    # 4A2g energy
    e_a2g = 0.0
    
    # All quartet energies
    quartets = [eigvals_t1g[0], eigvals_t1g[1], e_t2g, e_a2g]
    ground_quartet = min(quartets)
    
    # Doublets for d7 are hole-analogs of d3.
    # For d7 low spin, the ground state is 2T2g.
    # The energy of 2T2g relative to 4A2g:
    # From Tanabe-Sugano, 2T2g relative to 4T1g (F) is approximately:
    # E(2T2g) - E(4T1g) = delta - (some value)
    # A better way is to use the energy of 2T2g:
    # For d7, E(2T2g) = -0.6*delta - 3B + ... ? No.
    # Let's use the values from a TS diagram for d7:
    # At Dq/B=3.0, E(4T1g) is above E(2T2g).
    # Actually, E(2T2g) is the ground state for Dq/B > 2.5.
    # Let's approximate the gap.
    
    return quartets, ground_quartet

for dq_b in [1.45, 2.45, 3.00]:
    q, g = solve_d7(dq_b)
    print(f"Dq/B={dq_b}: ground_q={g}, quartets={q}")
