import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(orbs)
_w={}
def w3(*a):
    if a not in _w: _w[a]=float(wigner_3j(*a))
    return _w[a]
def ang(k,m1,q,m2):
    if m1!=m2+q: return 0.0
    red=(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
    return (-1)**(l-m1)*w3(l,k,l,-m1,q,m2)*red
def Vparts(ma,sa,mb,sb,mc,sc,md,sd):
    if sa!=sc or sb!=sd: return None
    out=[]
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*ang(k,ma,q,mc)*ang(k,mb,-q,md)
        out.append(s)
    return out
def build_V(F):
    V=np.zeros((N,N,N,N))
    for a in range(N):
     for b in range(N):
      for c in range(N):
       for d in range(N):
        p=Vparts(*orbs[a],*orbs[b],*orbs[c],*orbs[d]) if True else None
        if p is None: continue
        V[a,b,c,d]=sum(F[i]*p[i] for i in range(3))
    return V
ms=list(range(-2,3))
W=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        W[i,j]=ang(4,m1,0,m2)+sqrt(5/14)*(ang(4,m1,4,m2)+ang(4,m1,-4,m2))
print("cubic W eig:",np.round(np.linalg.eigvalsh(W),5))
