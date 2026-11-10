
mkdir -p ~/w && cd ~/w && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j as w
from scipy.optimize import fsolve
ms=[2,1,0,-1,-2]
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*w(2,k,2,-m1,q,m2)*w(2,k,2,0,0,0))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),6)); idx={d:i for i,d in enumerate(dets)}
# restrict to Sz=0, Lz irrelevant
dets=[d for d in dets if sum(1 if so[i][1]==0 else -1 for i in d)==0]; idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def ap(op,d):  # apply a+ or a: returns (sign,newdet)
    pass
def ann(p,d):
    if p not in d: return 0,None
    pos=d.index(p); return (-1)**pos, tuple(x for x in d if x!=p)
def cre(p,d):
    if p in d: return 0,None
    pos=sum(1 for x in d if x<p); return (-1)**pos, tuple(sorted(d+(p,)))
def V2(p,q,r,s,F):
    (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r],so[s]
    if sa!=sc or sb!=sd or a+b!=c+d: return 0
    return sum(Ck[(k,a,c)]*Ck[(k,d,b)]*F[k] for k in (2,4))
nz=[]
def H(B,C,Dq):
    F={2:49*(B+C/7),4:441*C/35}
    h=np.zeros((N,N))
    Vm=np.zeros((5,5))
    for i,m in enumerate(ms): Vm[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    Vm[0,4]=Vm[4,0]=5*Dq
    one=[(p,q,Vm[p//2 if False else ms.index(so[p][0]),ms.index(so[q][0])]) for p in range(10) for q in range(10) if so[p][1]==so[q][1]]
    two=[(p,q,r,s,V2(p,q,r,s,F)) for p in range(10) for q in range(10) for r in range(10) for s in range(10)]
    two=[t for t in two if abs(t[4])>1e-12 and p!=q] if False else [t for t in two if abs(t[4])>1e-12 and t[0]!=t[1] and t[2]!=t[3]]
    for j,d in enumerate(dets):
        for p,q,v in one:
            if v==0: continue
            s1,d1=ann(q,d)
            if not s1: continue
            s2,d2=cre(p,d1)
            if s2 and d2 in idx: h[idx[d2],j]+=v*s1*s2
        for p,q,r,s,v in two:
            s1,d1=ann(r,d)
            if not s1: continue
            s2,d2=ann(s,d1)
            if not s2: continue
            s3,d3=cre(q,d2)
            if not s3: continue
            s4,d4=cre(p,d3)
            if s4 and d4 in idx: h[idx[d4],j]+=0.5*v*s1*s2*s3*s4
    return h
def levels(B,C,Dq):
    e=np.linalg.eigvalsh(H(B,C,Dq)); return e
def tr(x):
    Dq,B=x
    e=levels(B,4.5*B,Dq); e=np.round(e-e[0],3)
    u=sorted(set(np.round(e,2)))
    return e
import sys
Dq,B=2000,600
e=levels(B,4.5*B,Dq); e-=e[0]
print(sorted(set(np.round(e,1)))[:12])
E
python3 a.py