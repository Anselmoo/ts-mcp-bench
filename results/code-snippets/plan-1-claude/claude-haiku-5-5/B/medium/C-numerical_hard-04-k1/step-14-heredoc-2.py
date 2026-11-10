import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
N=10
def Ang(mi,mk,K,q):
    if -mi+mk-q!=0 or abs(q)>K: return 0.0
    return (-1)**(mi)*((-1)**q)*float(gaunt(2,2,K,-mi,mk,-q))
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
dets=list(itertools.combinations(range(N),5)); idx={d:n for n,d in enumerate(dets)}
nd=len(dets)
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
conn2=[];conn1=[]
for n,d in enumerate(dets):
    for (i,j,k,ll),dd in W.items():
        s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
        if s is not None: conn2.append((idx[s],n,sg,dd))
    for i in range(N):
        for k in range(N):
            if orbs[i][1]!=orbs[k][1]: continue
            s,sg=apply_ops(d,[('a',k),('c',i)])
            if s is not None: conn1.append((idx[s],n,sg,i,k))
Sp=np.zeros((nd,nd))
for n,d in enumerate(dets):
    for m in ms:
        s,sg=apply_ops(d,[('a',orbs.index((m,1))),('c',orbs.index((m,0)))])
        if s is not None: Sp[idx[s],n]+=sg
Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
S2=Sp.T@Sp+np.diag(Szv**2+Szv)
w,U=np.linalg.eigh(S2)
P=U[:,np.abs(w-0.75)<1e-6]
# precompute 2e operator matrices for K=2 and K=4 separately (Dq,B,C independent)
M2=np.zeros((nd,nd)); M4=np.zeros((nd,nd)); M1=np.zeros((nd,nd,5,5))
for a,n,sg,dd in conn2:
    M2[a,n]+=0.5*sg*dd[2]; M4[a,n]+=0.5*sg*dd[4]
# one-electron pieces: Dq coefficients: t2g part and eg part as operators on the 5x5 orbital matrix
Ht=np.zeros((nd,nd)); He=np.zeros((nd,nd))
def onebody(h):
    h1=np.zeros((N,N),complex)
    for i,(mi,si) in enumerate(orbs):
        for k,(mk,sk) in enumerate(orbs):
            if si==sk: h1[i,k]=h[mi+2,mk+2]
    H=np.zeros((nd,nd),complex)
    for a,n,sg,i,k in conn1: H[a,n]+=sg*h1[i,k]
    return H
Ot=sum(onebody(-4*np.outer(v,v.conj())) for v in t2g)
Oe=sum(onebody(6*np.outer(v,v.conj())) for v in eg)
Ot=np.real_if_close(Ot); Oe=np.real_if_close(Oe)
# Dq-coefficient operator = -4*Ot_unit + 6*Oe_unit (Ot,Oe already include -4,6 factors); Dq operator = Ot+Oe with Dq=1
OD=(Ot+Oe)
np.savez('/tmp/ops.npz',M2=M2,M4=M4,OD=np.real(OD),P=P)
print("saved", P.shape)
