import numpy as np
from scipy.optimize import least_squares
import d7
F0=1.0
def H(Dq,B,C):
    F2 = 49*B + 7*C; F4 = 63*C/5
    M = sum(Dq*d7.fieldDq[o]*d7.ONEs[o] for o in range(5))
    M = M + d7.Ts[0]*F0 + d7.Ts[1]*F2 + d7.Ts[2]*F4
    return M
# check: Ms=3/2 sector spectrum via S2 eigen
Hm = H(0.0, 1000.0, 4000.0)
# eigen decomposition joint: diagonalize H + mu*S2 to separate spins
mu = 1e5
ev, V = np.linalg.eigh(Hm + mu*d7.S2s)
S2v = np.einsum('ik,ij,jk->k', V, d7.S2s, V)
E = np.einsum('ik,ij,jk->k', V, Hm, V)
for e,s in sorted(zip(E,S2v))[:40]:
    print(round(e,2), round(s,3))
