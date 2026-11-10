
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
l=2; ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (1,-1)]
N=len(orbs)
@lru_cache(None)
def G(k,m1,m3,q):
    return complex(gaunt(l,k,l,-m1,q,m3))*(-1)**m1
def ang(k,m1,m3,m2,m4):
    s=0
    for q in range(-k,k+1):
        s+= np.conj(G(k,m1,m3,q)) * G(k,m2,m4,q)
    return (s*4*np.pi/(2*k+1)).real
def Vee_full(F):
    V=np.zeros((N,N,N,N))
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
      for a,(m3,s3) in enumerate(orbs):
       for b,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4: continue
        V[i,j,a,b]=sum(Fk*ang(k,m1,m3,m2,m4) for k,Fk in zip((0,2,4),F))
    return V
dets=list(itertools.combinations(range(N),5))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det, ops):
    occ=list(det); sign=1
    for op,i in reversed(ops):
        if op=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign, tuple(occ)
def build(F, Dq, Vcache=None):
    V=Vee_full(F) if Vcache is None else Vcache
    M=len(dets)
    H=np.zeros((M,M),dtype=complex)
    s2=np.sqrt(2)
    def vec(d):
        v=np.zeros(5,dtype=complex)
        for m,c in d.items(): v[m+2]=c
        return v
    orbR=[vec({-2:1j/s2,2:-1j/s2}), vec({2:1/s2,-2:1/s2}), vec({-1:1j/s2,1:1j/s2}), vec({-1:1/s2,1:-1/s2}), vec({0:1})]
    hR=np.diag([-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq]).astype(complex)
    Uc=np.array(orbR).T
    h=Uc@hR@Uc.conj().T
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
        if s1!=s2: continue
        hv=h[m1+2,m2+2]
        if abs(hv)<1e-12: continue
        for d in dets:
            r=apply_ops(d,[('c',i),('a',j)])
            if r is None: continue
            sg,nd=r
            H[idx[nd],idx[d]]+= sg*hv
    for i in range(N):
     for j in range(N):
      for k in range(N):
       for l_ in range(N):
        v=V[i,j,k,l_]
        if abs(v)<1e-12 or i==j or k==l_: continue
        for d in dets:
            r=apply_ops(d,[('c',i),('c',j),('a',l_),('a',k)])
            if r is None: continue
            sg,nd=r
            H[idx[nd],idx[d]]+=0.5*sg*v
    return H
EOF
cat << 'EOF' > test.py
import numpy as np, collections
from d5 import *
# Ms=3/2 subspace: 4 up,1 down
sub=[i for i,d in enumerate(dets) if sum(orbs[x][1] for x in d)==3]
H=build((1.0,0,0),0.0)
Hs=H[np.ix_(sub,sub)]
w=np.linalg.eigvalsh(Hs.real)
print(len(sub), collections.Counter(np.round(w,6)))
EOF
timeout 500 python3 test.py
