# This is a simplified attempt to find the energy of the 3T1g state.
# The diagonal elements for the T1g states in d4 are:
# E(3F) - 6Dq
# E(3P) - 12Dq
# E(3D) - 6Dq
# We need the crossover where the lowest eigenvalue = -6Dq.
# Since the lowest eigenvalue is always <= the minimum diagonal element,
# the crossover must happen when the minimum diagonal element is >= -6Dq.
# Min diagonal element is min(E(3F) - 6Dq, E(3P) - 12Dq).
# E(3F) - 6Dq = -6Dq  => E(3F) = 0. (But E(3F) is not 0).
# E(3P) - 12Dq = -6Dq => 6Dq = E(3P) = 15B.

B = 706
C = 2734
# E(3P) = 15 * B
Dq_crossover = (15 * B) / 6
print(f"Dq_crossover = {Dq_crossover}")
