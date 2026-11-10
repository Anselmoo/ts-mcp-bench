cd ~ && python3 - <<'EOF'
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
conn2=[]
for n,d in enumerate(dets):
    for (i,j,k,ll),dd in W.items():
        s,sg=apply_ops(d,[('a',k),('a',ll),('c',j),('c',i)])
        if s is None: continue
        conn2.append((idx[s],n,sg,dd))
conn1=[]
for n,d in enumerate(dets):
    for i in range(N):
        for k in range(N):
            if orbs[i][1]!=orbs[k][1]: continue
            s,sg=apply_ops(d,[('a',k),('c',i)])
            if s is None: continue
            conn1.append((idx[s],n,sg,i,k))
Sp=np.zeros((252,252))
for n,d in enumerate(dets):
    for m in ms:
        iu=orbs.index((m,0)); idn=orbs.index((m,1))
        s,sg=apply_ops(d,[('a',idn),('c',iu)])
        if s is not None: Sp[idx[s],n]+=sg
Szv=np.array([sum(0.5 if orbs[p][1]==0 else -0.5 for p in d) for d in dets])
S2=Sp.T@Sp+np.diag(Szv**2+Szv)
def H_of(Dq,B,C):
    F={0:0.0,2:49*B+7*C,4:12.6*C}
    h=np.zeros((5,5),complex)
    for v in t2g: h+=-4*Dq*np.outer(v,v.conj())
    for v in eg: h+=6*Dq*np.outer(v,v.conj())
    h1=np.zeros((N,N),complex)
    for i,(mi,si) in enumerate(orbs):
        for k,(mk,sk) in enumerate(orbs):
            if si==sk: h1[i,k]=h[mi+2,mk+2]
    H=np.zeros((252,252),complex)
    for (a,n,sg,i,k) in conn1: H[a,n]+=sg*h1[i,k]
    for (a,n,sg,dd) in conn2:
        H[a,n]+=0.5*sg*sum(F[K]*dd[K] for K in (2,4))
    return H
H=H_of(1000,500,2200)
print("herm",np.allclose(H,H.conj().T))
w,U=np.linalg.eigh(S2)
print("S2 eigen counts", [ (round(x,2),int(np.sum(np.abs(w-x)<1e-6))) for x in np.unique(np.round(w,4))])
P=U[:,np.abs(w-0.75)<1e-6]
ev=np.linalg.eigvalsh(P.conj().T@H@P)
print(np.round(ev[:12],2))
print("full H lowest", np.round(np.linalg.eigvalsh(H)[:10],2))
EOF