
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=922.,4156.
F2=(B*49+C*49/7*0)  # compute properly below
# B=F2-5F4, C=35F4 with F2=F^2/49, F4=F^4/441
f4=C/35; f2=B+5*f4
Fk={0:0.0,2:f2*49,4:f4*441}
ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) for l=2
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(5*5)*np.sqrt(4*np.pi/(2*k+1))*0+0) 
from sympy.physics.wigner import wigner_3j
def ckf(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ckf(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def g(a,b,c,d): # <ab|1/r|cd> spatial orbitals m
    if a+b!=c+d: return 0.
    return sum(CK[(k,a,c)]*CK[(k,d,b)]*Fk[k] for k in (0,2,4))
# crystal field octahedral: Dq; eg (m=0,±2 combos). matrix in m basis
V=np.zeros((5,5))
idx={m:i for i,m in enumerate(ml)}
V[idx[0],idx[0]]=6; V[idx[1],idx[1]]=-4; V[idx[-1],idx[-1]]=-4
V[idx[2],idx[2]]=1; V[idx[-2],idx[-2]]=1; V[idx[2],idx[-2]]=5; V[idx[-2],idx[2]]=5
n=7
basis=list(itertools.combinations(range(10),n))
bi={b:i for i,b in enumerate(basis)}
N=len(basis)
def sign_apply(det, rem, add):
    # annihilate rem (list), create add; return sign,newdet
    d=list(det); s=1
    for r in rem:
        if r not in d: return 0,None
        p=d.index(r); s*=(-1)**p; d.pop(p)
    for a in reversed(add):
        if a in d: return 0,None
        d.insert(0,a)
    # sort
    perm=sorted(range(len(d)),key=lambda i:d[i])
    # sign of permutation
    dd=d[:]; sg=1
    for i in range(len(dd)):
        for j in range(len(dd)-1-i):
            if dd[j]>dd[j+1]: dd[j],dd[j+1]=dd[j+1],dd[j]; sg=-sg
    return s*sg,tuple(dd)
H1=np.zeros((N,N)); H2=np.zeros((N,N))
for i,det in enumerate(basis):
    for p in det:
        for q in range(10):
            mp,sp=orbs[p]; mq,sq=orbs[q]
            if sp!=sq: continue
            v=V[idx[mq],idx[mp]]
            if v==0: continue
            s,nd=sign_apply(det,[p],[q])
            if s: H1[bi[nd],i]+=s*v
    for p1,p2 in itertools.combinations(det,2):
        for q1 in range(10):
            for q2 in range(10):
                if q1==q2: continue
                m1,s1=orbs[p1];m2,s2=orbs[p2];n1,t1=orbs[q1];n2,t2=orbs[q2]
                if s1!=t1 or s2!=t2: continue
                v=g(n1,n2,m1,m2)
                if v==0: continue
                s,nd=sign_apply(det,[p2,p1],[q1,q2])
                if s: H2[bi[nd],i]+=s*v
# Sz=1/2 subspace contains all; compute S^2 for ground state
Sz=np.array([sum(0.5 if orbs[o][1] else -0.5 for o in d) for d in basis])
sel=np.where(Sz==1.5)[0]; sel2=np.where(Sz==0.5)[0]
def gaps(Dq):
    e4=np.linalg.eigvalsh((H2+Dq*H1)[np.ix_(sel,sel)])[0]
    e2=np.linalg.eigvalsh((H2+Dq*H1)[np.ix_(sel2,sel2)])[0]
    return e2-e4
print(brentq(gaps,500,5000))
Dq=brentq(gaps,500,5000)
import math
e4=7.5*B-3*Dq-0.5*math.sqrt(225*B*B+100*Dq*Dq+180*B*Dq)
print(Dq,e4)
EOF
python3 /tmp/d7.py
