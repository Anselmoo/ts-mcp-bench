import numpy as np
from scipy.linalg import expm
import d7
from sym import rot_matrix
from math import pi
def Rz(phi):
    return np.array([[np.cos(phi),-np.sin(phi),0],[np.sin(phi),np.cos(phi),0],[0,0,1.]])
h=1e-4
K = (rot_matrix(Rz(h)) - rot_matrix(Rz(-h)))/(2*h)   # d/dphi U(phi) at 0
# Check: U(phi) = expm(phi*K0) with K0 generator; K0 = K at phi=0
K10 = np.kron(K, np.eye(2))
G = sum(K10[p,q]*d7.cd[p]@d7.c[q] for p in range(10) for q in range(10) if abs(K10[p,q])>1e-12)
Gs = G[d7.idx][:,d7.idx].toarray()
Gam = expm(Gs*pi/2)
# sanity: Gam^4 should be identity
print("C4^4=1:", np.allclose(np.linalg.matrix_power(Gam,4),np.eye(len(Gam)),atol=1e-6))
np.save('Gam.npy', Gam)
