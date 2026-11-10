def find_crossover(B, C):
    # The crossover point for d4 octahedral is when 10Dq = P.
    # P is the pairing energy. For d-electrons, P = 3C - 2B is a common simplification.
    # However, let's look for a more precise formula for d4.
    # The energy of the 5Eg state is -6 Dq.
    # The energy of the 3T1g state (low spin) can be expressed in terms of Racah parameters.
    # For d4, E(3T1g) = -12 Dq + 6B + something?
    # Let's use the relation 10Dq = P where P = (Energy of 3T1g at Dq=0) - (Energy of 5Eg at Dq=0).
    # Actually, the pairing energy P for d4 is often given as P = 3C - 2B.
    # Let's check this formula.
    P = 3 * C - 2 * B
    Dq_crossover = P / 10.0
    return Dq_crossover

B = 706
C = 2734
print(f"Dq_crossover = {find_crossover(B, C)}")
