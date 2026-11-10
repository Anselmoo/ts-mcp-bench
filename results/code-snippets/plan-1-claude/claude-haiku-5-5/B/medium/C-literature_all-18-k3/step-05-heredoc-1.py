import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
from functools import lru_cache
l=2; ms=list(range(-2,3))
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def tensor(k,q,m1,m3):
    if m1-m3!=q: return 0.0
    red=(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
    return (-1)**(l-m1)*w3(l,k,l,-m1,q,m3)*red
def cmat(k,q): return np.array([[tensor(k,q,m1,m3) for m3 in ms] for m1 in ms])
V = cmat(4,0)+np.sqrt(5/14)*(cmat(4,4)+cmat(4,-4))
ev=np.linalg.eigvalsh(V.astype(complex))
print("cubic eig raw", np.round(ev,5))
