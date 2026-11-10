import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
t2g=[vec({-2:1/(1j*r2),2:-1/(1j*r2)}), vec({-1:-1/r2,1:1/r2}), vec({-1:1/(1j*r2),1:1/(1j*r2)})]
eg=[vec({0:1}), vec({-2:1/r2,2:1/r2})]
def apply_ops(state, ops):
    s=list(state); sign=1
    for typ,p in ops:
        if typ=='a':
            if p not in s: return None,0
            pos=s.index(p); sign*=(-1)**pos; s.pop(pos)
        else:
            if p in s: return None,0
            pos=sum(1 for x in s if x<p); sign*=(-1)**pos; s.insert(pos,p)
    return tuple(s),sign
dets=list(itertools.combinations(range(N),5))
idx={d:n for n,d in enumerate(dets)}
Dq=1.0
h=np.zeros((5,5),complex)
for v in t2g: h+=-4*Dq*np.outer(v,v.conj())
for v in eg: h+=6*Dq*np.outer(v,v.conj())
print(np.round(h,3))
h1=np.zeros((N,N),complex)
for i,(mi,si) in enumerate(orbs):
    for k,(mk,sk) in enumerate(orbs):
        if si==sk: h1[i,k]=h[mi+2,mk+2]
H=np.zeros((252,252),complex)
for n,d in enumerate(dets):
    for i in range(N):
        for k in range(N):
            if h1[i,k]==0: continue
            s,sg=apply_ops(d,[('a',k),('c',i)])
            if s is None: continue
            H[idx[s],n]+=sg*h1[i,k]
print(np.round(np.linalg.eigvalsh(H)[:8],4))
