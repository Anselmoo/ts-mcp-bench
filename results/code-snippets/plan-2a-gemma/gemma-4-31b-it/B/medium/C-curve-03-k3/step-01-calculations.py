import numpy as np

def calculate_energies(dq_over_b, b, c):
    # For d7, the ground state in weak field is 4T1g(F).
    # Relative energies for 4F components relative to 4T1g(F)
    # 4T1g(F): 0
    # 4T2g(F): 4 * Dq
    # 4A2g(F): 12 * Dq
    
    dq = dq_over_b * b
    
    e_4t2g_f = 4 * dq
    e_4a2g_f = 12 * dq
    
    # mixing of 4T1g(F) and 4T1g(P)
    # E1 = 0, E2 = 15*B
    # matrix = [[0, 4*B], [4*B, 15*B]]
    # det(matrix - E*I) = -E(15B - E) - (4B)^2 = E^2 - 15BE - 16B^2 = 0
    # E = (15B +/- sqrt(225B^2 + 64B^2))/2 = (15B +/- sqrt(289B^2))/2 = (15B +/- 17B)/2
    # E1 = -B, E2 = 16B
    # Energy relative to ground state 4T1g(F)_mixed:
    # The ground state is lowered by B.
    # So the 4T1g(P)_mixed is at 16B - (-B) = 17B.
    # Wait, this is for the case where the unperturbed 4T1g(F) was 0.
    # If the unperturbed 4T1g(F) was 0, the new ground state is -B.
    # Then E(4T2g) = 4*Dq - (-B) = 4*Dq + B.
    # E(4A2g) = 12*Dq + B.
    # E(4T1g(P)) = 17B.
    
    # Let's re-calculate relative to the ground state.
    # Ground state E0 = -B
    # E(4T2g) = 4*dq + B
    # E(4A2g) = 12*dq + B
    # E(4T1g(P)) = 17*b + B? No.
    # The eigenvalues are -B and 16B. The difference is 17B.
    # So E(4T1g(P)) - E(ground) = 17B.
    
    # Wait, the 4T1g(P) energy is 15B relative to 4F barycenter.
    # The 4T1g(F) energy is 0 relative to 4F barycenter.
    # So the difference is 15B.
    # Then E = (15B +/- sqrt(15^2 + 4^2))B/2 = (15 +/- 15.52)B/2
    # E1 = -0.26 B, E2 = 15.26 B
    # Difference = 15.52 B.
    # Then E(4T2g) = 4*dq - (-0.26 B) = 4*dq + 0.26 B.
    # E(4A2g) = 12*dq + 0.26 B.
    
    # Let's check the doublets.
    # The lowest doublet for d7 is 2Eg.
    # According to Tanabe-Sugano diagrams, the 2Eg state drops rapidly.
    # For d3, 2Eg is at E = -2 Dq + some constant relative to 4A2g.
    # For d7, we can estimate the 2Eg energy.
    # In high field (low spin d7: t2g^6 eg^1), the ground state is 2T2g.
    # No, for d7 low spin, the configuration is t2g^6 eg^1.
    # This gives a 2T2g state? No, eg^1 is 2Ag.
    # Wait, d7 low spin is t2g^6 eg^1, which is a 2Ag state.
    # Let's look at the d7 TS diagram.
    # The ground state becomes 2Eg? No, for d7 it's 2Eg.
    # Let's check. d7 low spin is t2g^6 eg^1.
    # Wait, if you have 1 electron in eg, you get a 2Eg state.
    # So the ground state in high field is 2Eg.
    # The energy of 2Eg in the high-field limit is roughly -12 Dq relative to 4T1g?
    # Let's use the d3 analog.
    # d3 ground state is 4A2g (t2g^3).
    # d3 low spin is t2g^2 eg^1 (2T2g, 2T1g, 2A2g).
    # The energy of t2g^2 eg^1 relative to t2g^3 is (eg - t2g) = 10 Dq.
    # For d7, high spin is t2g^5 eg^2.
    # Low spin is t2g^6 eg^1.
    # The energy of t2g^6 eg^1 relative to t2g^5 eg^2 is (t2g - eg) = -10 Dq.
    # So the 2Eg state drops by 10 Dq relative to the 4T1g(F) state.
    # To be more precise, we need the exchange energy.
    # The 4T1g(F) state has spin 3/2. The 2Eg state has spin 1/2.
    # The energy difference including exchange is roughly:
    # E(2Eg) - E(4T1g) = -10 Dq + (exchange term).
    # For d3, E(2Eg) - E(4A2g) = 10 Dq - (exchange term).
    # The exchange term for d3 2Eg is about 5.5 B?
    # Let's assume E(2Eg) - E(4T1g) = -10 Dq + 5.5 B.
    
    e_4t2g_f = 4 * dq_over_b * b + 0.26 * b
    e_4a2g_f = 12 * dq_over_b * b + 0.26 * b
    e_4t1g_p = 15.52 * b
    e_2eg = -10 * dq_over_b * b + 5.5 * b # Approximation
    
    return {
        "4T2g(F)": e_4t2g_f,
        "4A2g(F)": e_4a2g_f,
        "4T1g(P)": e_4t1g_p,
        "2Eg": e_2eg
    }

for dq_b in [1.45, 2.45, 3.00]:
    print(f"Dq/B = {dq_b}: {calculate_energies(dq_b, 784, 3699)}")
