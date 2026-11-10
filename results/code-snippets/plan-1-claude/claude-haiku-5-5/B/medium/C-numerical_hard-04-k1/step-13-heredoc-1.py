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
A={(K,q,mi,mk):Ang(mi,mk,K,q) for K in (0,2,4) for q in range(-K,K+1) for mi in ms for mk in ms}
W={}
for i,(mi,si) in enumerate(orbs):
 for k,(mk,sk) in enumerate(orbs):
  if si!=sk: continue
  for j,(mj,sj) in enumerate(orbs):
   for ll,(ml,sl) in enumerate(orbs):
    if sj!=sl: continue
    d={K:4*np.pi/(2*K+1)*sum(((-1)**q)*A[(K,q,mi,mk)]*A[(K,-q,mj,ml)] for q in range(-K,K+1)) for K in (0,2,4)}
    if any(abs(v)>1e-12 for v in d.values()): W[(i,j,k,ll)]=d
def run(nel,B,C):
    dets=list(itertools.combinations(range(N),nel)); idx={d:n for n,d in enumerate(dets)}
    F={0:0.0,2:49*B+7*C,4:12.6*C}
    H=np.zeros((len(dets),)*2)
    for n,d in enumerate(dets):
        for (i,j,k,ll),dd in W.items():
            s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
            if s is None: continue
            H[idx[s],n]+=0.5*sg*sum(F[K]*dd[K] for K in (2,4))
    Sp=np.zeros((len(dets),)*2)
    for n,d in enumerate(dets):
        for m in ms:
            s,sg=apply_ops(d,[('a',orbs.index((m,1))),('c',orbs.index((m,0)))])
            if s is not None: Sp[idx[s],n]+=sg
    Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
    S2=Sp.T@Sp+np.diag(Szv**2+Szv)
    w,U=np.linalg.eigh(S2)
    out={}
    for S in sorted(set(np.round(w,6))):
        P=U[:,np.abs(w-S)<1e-6]
        ev=np.linalg.eigvalsh(P.conj().T@H@P)
        out[S]=np.round(np.unique(np.round(ev,4)),3)
    return out
# d2: test 3F(triplet S=1), 3P, 1D (singlet S=0), with B=1, C=4 (C/B arbitrary)
for C in (0,4):
    o=run(2,1.0,C)
    print("C=",C,{k:v for k,v in o.items()})
