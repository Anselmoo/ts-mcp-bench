import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=803.;C=3078.
F2=49*B+7*C;F4=63*C/5
F={0:0,2:F2,4:F4}
orb=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*5) if True else 0
import functools
@functools.lru_cache(None)
def c(k,m1,m2):
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2))
def V(a,b,cc,d): # <ab|1/r12|cd>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cc,d
    if s1!=s3 or s2!=s4: return 0
    t=0
    for k in (0,2,4):
        if m1-m3==m4-m2:
            t+=F[k]*c(k,m1,m3)*c(k,m4,m2)  # check
    return t
# note: <ab|cd> = sum_k c^k(m1,m3)c^k(m4,m2) F^k
dets=[d for d in itertools.combinations(range(10),6) if sum(orb[i][1] for i in d)==0]
idx={d:i for i,d in enumerate(dets)}
# cubic field: real d orbitals; use complex basis one-body: Dq operator in m basis
def h1(Dq):
    H=np.zeros((10,10))
    # eg: dz2 (m=0), (|2>+|-2>)/√2 ; t2 rest. V = 6Dq on eg, -4Dq on t2g
    P=np.zeros((5,5)) # m=-2..2
    def vec(d):
        v=np.zeros(5);
        for m,x in d.items(): v[m+2]=x
        return v
    e1=vec({0:1});e2=vec({2:2**-.5,-2:2**-.5})
    Pe=np.outer(e1,e1)+np.outer(e2,e2)
    Pt=np.eye(5)-Pe
    h=6*Dq*Pe-4*Dq*Pt
    for i,(m,s) in enumerate(orb):
        for j,(n,t) in enumerate(orb):
            if s==t: H[i,j]=h[m+2,n+2]
    return H
def apply_ops(dt,ops):
    pass
def build(Dq):
    n=len(dets);H=np.zeros((n,n))
    h=h1(Dq)
    # slater rules via second quantization
    def ann_cre(det,ops):
        d=list(det);sign=1
        for typ,p in ops:
            if typ=='a':
                if p not in d:return None,0
                k=d.index(p);sign*=(-1)**k;d.pop(k)
            else:
                if p in d:return None,0
                k=sum(1 for x in d if x<p);sign*=(-1)**k;d.insert(k,p)
        return tuple(d),sign
    for det in dets:
        j=idx[det]
        for p in range(10):
            for q in range(10):
                if h[p,q]!=0:
                    nd,s=ann_cre(det,[('a',q),('c',p)])
                    if nd in idx:H[idx[nd],j]+=s*h[p,q]
    return H
Vl=[]
for p in range(10):
 for q in range(10):
  for r in range(10):
   for s in range(10):
    v=V(orb[p],orb[q],orb[r],orb[s])
    if v!=0: Vl.append((p,q,r,s,v))
def ann_cre(det,ops):
    d=list(det);sign=1
    for typ,p in ops:
        if typ=='a':
            if p not in d:return None,0
            k=d.index(p);sign*=(-1)**k;d.pop(k)
        else:
            if p in d:return None,0
            k=sum(1 for x in d if x<p);sign*=(-1)**k;d.insert(k,p)
    return tuple(d),sign
n=len(dets);HV=np.zeros((n,n))
for det in dets:
    j=idx[det]
    for p,q,r,s,v in Vl:
        nd,sg=ann_cre(det,[('a',s),('a',r),('c',q),('c',p)])
        if nd in idx:HV[idx[nd],j]+=0.5*sg*v
def E(Dq):
    w=np.linalg.eigvalsh(HV+build(Dq)); return w
# identify: lowest at small Dq is 5T2 ; at large Dq 1A1. compare lowest S=2 state vs lowest singlet: use total
# Use Sz=0 spectrum: lowest eigenvalue overall is ground state; find Dq where ground state energy has kink: compare 5T2 energy = min with S=2: use Sz=0 can't separate; instead track via formula
# compute S=2 energies by diagonalising with S^2
S2=np.zeros((n,n))
for det in dets:
    j=idx[det]
    # S^2 = S-S+ + Sz^2+Sz ; Sz=0
    for p in range(10):
        pass
def Sminus_plus():
    M=np.zeros((n,n))
    for det in dets:
        j=idx[det]
        for i,(m,s) in enumerate(orb):
            if s==0.5:
                # S+ then S-: S-S+ ; use direct: sum over orbital pairs
                pass
    return M
# simpler: S^2 = sum_{ij} a†_{i↓}a_{i↑}... build S+ on Sz=0->1 not in space; do S^2 = S-S+ with intermediate
def Sp(det):
    out={}
    for i,(m,s) in enumerate(orb):
        if s==-0.5:
            up=i-1 # ordering (m,+.5) then (m,-.5)
            nd,sg=ann_cre(det,[('a',i),('c',up)])
            if nd:out[nd]=out.get(nd,0)+sg
    return out
def Sm(det):
    out={}
    for i,(m,s) in enumerate(orb):
        if s==0.5:
            dn=i+1
            nd,sg=ann_cre(det,[('a',i),('c',dn)])
            if nd:out[nd]=out.get(nd,0)+sg
    return out
for det in dets:
    j=idx[det]
    for d1,c1 in Sp(det).items():
        for d2,c2 in Sm(d1).items():
            S2[idx[d2],j]+=c1*c2
def gs(Dq,S):
    H=HV+build(Dq)
    w,v=np.linalg.eigh(S2)
    sel=v[:,abs(w-S*(S+1))<1e-6]
    return np.linalg.eigvalsh(sel.T@H@sel).min()
f=lambda Dq:gs(Dq,2)-gs(Dq,0)
for D in (1000,1500,2000,2500,3000): print(D,f(D))
print(brentq(f,1000,3500))
