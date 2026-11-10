import numpy as np

Dq = 568.636
B = 1446.374
Delta = 10 * Dq
term1 = 15 * B - Delta
term2 = (15 * B + Delta)**2 + 144 * B**2
e_t1f = (term1 - np.sqrt(term2)) / 2
e_t1p = (term1 + np.sqrt(term2)) / 2
e_t2g = Delta
e_a2g = 3 * Delta

print(f"nu1: {e_t2g - e_t1f}")
print(f"nu2: {e_a2g - e_t1f}")
print(f"nu3: {e_t1p - e_t1f}")
