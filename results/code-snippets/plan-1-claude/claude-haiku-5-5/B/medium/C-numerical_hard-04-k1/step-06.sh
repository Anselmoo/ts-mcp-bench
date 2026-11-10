cd /tmp && python3 - <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
def Ang(mi,mk,K,q):
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
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
A={(K,q,mi,mk):Ang(mi,mk,K,q) for K in (0,2,4) for q in range(-K,K+1) for mi in ms for mk in ms}
W={}
for i,(mi,si) in enumerate(orbs):
 for k,(mk,sk) in enumerate(orbs):
  if si!=sk: continue
  for j,(mj,sj) in enumerate(orbs):
   for ll,(ml,sl) in enumerate(orbs):
    if sj!=sl: continue
    d={K:4*np.pi/(2*K+1)*sum(A[(K,q,mi,mk)]*A[(K,-q,mj,ml)] for q in range(-K,K+1)) for K in (0,2,4)}
    if any(abs(v)>1e-12 for v in d.values()): W[(i,j,k,ll)]=d
# Build pure 2e Hamiltonian per K separately
def Hk(K):
    H=np.zeros((252,252))
    for n,d in enumerate(dets):
        for (i,j,k,ll),dd in W.items():
            if abs(dd[K])<1e-14: continue
            s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
            if s is None: continue
            H[idx[s],n]+=0.5*sg*dd[K]
    return H
Sp=np.zeros((252,252))
for n,d in enumerate(dets):
    for m in ms:
        iu=orbs.index((m,0)); idn=orbs.index((m,1))
        s,sg=apply_ops(d,[('a',idn),('c',iu)])
        if s is not None: Sp[idx[s],n]+=sg
Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
S2=Sp.T@Sp+np.diag(Szv**2+Szv)
w,U=np.linalg.eigh(S2)
H0=Hk(0)
for K in (0,2,4):
    H=Hk(K)
    print("K",K)
    for S in (2.5,1.5,0.5):
        P=U[:,np.abs(w-(S*(S+1)))<1e-6]
        ev=np.linalg.eigvalsh(P.T@H@P)
        print(" S",S, np.round(np.unique(np.round(ev,4)),3))
EOF