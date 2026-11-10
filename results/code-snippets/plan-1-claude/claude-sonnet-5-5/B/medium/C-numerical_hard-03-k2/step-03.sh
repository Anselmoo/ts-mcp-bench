cd ~/w && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
def ak(k,a,b,c,d):
    q=a-c
    if q!=d-b: return 0
    return (-1)**q*ck(k,a,c)*ck(k,d,b)
A={k:np.zeros((5,5,5,5)) for k in(2,4)}
for k in (2,4):
  for a,b,c,d in itertools.product(range(5),repeat=4):
    A[k][a,b,c,d]=ak(k,ms[a],ms[b],ms[c],ms[d])
def h1(Dq):
    idx=lambda m:ms.index(m)
    v=np.zeros(5);v[idx(0)]=1;eg1=v
    v=np.zeros(5);v[idx(2)]=v[idx(-2)]=2**-.5;eg2=v
    P=np.outer(eg1,eg1)+np.outer(eg2,eg2)
    return 6*Dq*P-4*Dq*(np.eye(5)-P)
so=[(i,s) for s in (0,1) for i in range(5)]
dets=[c for c in itertools.combinations(range(10),5) if sum(so[i][1]==0 for i in c)==3]
di={d:i for i,d in enumerate(dets)}
def apply(det,ops):
    d=list(det);sign=1
    for (p,dag) in ops:
        if dag:
            if p in d: return None
            sign*=(-1)**sum(1 for x in d if x<p); d.append(p); d.sort()
        else:
            if p not in d: return None
            sign*=(-1)**d.index(p); d.remove(p)
    return tuple(d),sign
# precompute structures
one=[];two=[]
for j,det in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            r=apply(det,[(q,0),(p,1)])
            if r: one.append((di[r[0]],j,so[p][0],so[q][0],r[1]))
    for p,q,r_,s in itertools.product(range(10),repeat=4):
        if so[p][1]!=so[r_][1] or so[q][1]!=so[s][1]: continue
        a=(so[p][0],so[q][0],so[r_][0],so[s][0])
        if A[2][a]==0 and A[4][a]==0: continue
        r=apply(det,[(r_,0),(s,0),(q,1),(p,1)])
        if r: two.append((di[r[0]],j,a,r[1]))
def energies(Dq,B,C):
    F2=49*B+7*C;F4=63*C/5
    H1=h1(Dq);n=len(dets);H=np.zeros((n,n),complex)
    for i,j,p,q,s in one: H[i,j]+=H1[p,q]*s
    for i,j,a,s in two: H[i,j]+=0.5*s*(F2*A[2][a]/49+F4*A[4][a]/441)
    return np.linalg.eigvalsh(H)
E
python3 -c "
from a import *
e=energies(0,800,3680);print(np.round(e-e[0])[:30])
e=energies(500,800,3680);print(np.round(e-e[0])[:40])"