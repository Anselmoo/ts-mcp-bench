import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt, pi
l=2
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]
n=len(so)
def C(k,q,m,mp):
    if m-mp!=q: return 0.0
    return sqrt(4*pi/(2*k+1))*(-1)**m*float(gaunt(l,k,l,-m,q,mp))
M=lambda q: np.array([[C(4,q,m,mp) for mp in ms] for m in ms])
Moct=M(0)+sqrt(5/14)*(M(4)+M(-4))
print(np.round(Moct,4)); print("sym",np.allclose(Moct,Moct.T), np.allclose(Moct,Moct.conj().T))
print(np.round(np.linalg.eigvalsh(Moct),5))
