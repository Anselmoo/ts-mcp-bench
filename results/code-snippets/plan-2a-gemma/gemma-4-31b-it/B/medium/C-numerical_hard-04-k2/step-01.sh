cat << 'EOF' > solution.py
import numpy as np
from scipy.optimize import minimize

# For d5 low-spin octahedral, the ground state is 2T2g (t2g^5)
# The excited states from t2g^4 eg^1 configuration are 2A2g, 2T1g, 2T2g.
# Let's use the energies relative to t2g^5:
# E(2A2g) = 10Dq + f1(B, C)
# E(2T1g) = 10Dq + f2(B, C)
# E(2T2g) = 10Dq + f3(B, C)

# According to some sources, for the t2g^4 eg^1 configuration:
# The energies relative to the t2g^5 state are:
# nu1 = 10Dq - 4B + 3C
# nu2 = 10Dq + 8B + 3C
# nu3 = 10Dq + 8B + 3C + ... no.

# Let's try a different set of formulas:
# For a d5 low-spin system, the transitions from 2T2g to the t2g^4 eg^1 states are:
# E(2T1g) = 10Dq + 8B + 3C
# E(2A2g) = 10Dq - 4B + 3C
# E(2T2g_exc) = 10Dq + 8B + 3C + ... 
# Actually, the terms of t2g^4 eg^1 are 2A2g, 2T1g, 2T2g.
# The energy differences between them are proportional to B.
# E(2T2g_exc) - E(2T1g) = ?
# E(2T1g) - E(2A2g) = 12B

# Let's check if nu2 - nu1 = 12B or nu3 - nu2 = 12B or nu3 - nu1 = 12B
nu = np.array([29360, 29620, 31640])
diffs = []
for i in range(len(nu)):
    for j in range(i+1, len(nu)):
        diffs.append(nu[j] - nu[i])
print("Differences:", diffs)
EOF
python3 solution.py
