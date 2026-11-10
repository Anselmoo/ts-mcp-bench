cd ~ 2>/dev/null; python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
from scipy.optimize import brentq
l=2
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=10
def ang(k,m1,q,m2):
    if m1!=m2+q: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m1)*float(wigner_3j(l,k,l,-m1,q,m2))*red
ms=list(range(-2,3))
W=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        W[i,j]=ang(4,m1,0,m2)+sqrt(5/14)*(ang(4,m1,4,m2)+ang(4,m1,-4,m2))
scale=21.0  # 1-electron CF = Dq*scale*W -> t2g=-4Dq, eg=+6Dq
# Coulomb: F0,F2,F4 from Racah B,C
B,C=621.0,2851.0
F4=441*C/35; F2=(441*B+5*F4)/9; F0=0.0  # F0 only shifts all states; irrelevant for gaps
Fk=[F0,F2,F4]
# two-electron integrals
Vt=np.zeros((N,N,N,N))
for a,(ma,sa) in enumerate(orbs):
 for b,(mb,sb) in enumerate(orbs):
  for c,(mc,sc) in enumerate(orbs):
   for d,(md,sd) in enumerate(orbs):
    if sa!=sc or sb!=sd: continue
    tot=0.0
    for k,F in zip((0,2,4),Fk):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*ang(k,ma,q,mc)*ang(k,mb,-q,md)
        tot+=F*s
    Vt[a,b,c,d]=tot
# basis: all 5-electron subsets
dets=list(itertools.combinations(range(N),5))
idx={d:i for i,d in enumerate(dets)}
def apply_ann(st,i):
    if i not in st: return None
    sgn=(-1)**sum(1 for x in st if x<i)
    return sgn, tuple(x for x in st if x!=i)
def apply_cre(st,i):
    if i in st: return None
    sgn=(-1)**sum(1 for x in st if x<i)
    return sgn, tuple(sorted(st+(i,)))
def op2(st,a,b,c,d):  # a+_a a+_b a_d a_c
    r=apply_ann(st,c)
    if r is None: return None
    s1,st1=r
    r=apply_ann(st1,d)
    if r is None: return None
    s2,st2=r
    r=apply_cre(st2,b)
    if r is None: return None
    s3,st3=r
    r=apply_cre(st3,a)
    if r is None: return None
    s4,st4=r
    return s1*s2*s3*s4, st4
D=len(dets)
H=np.zeros((D,D))
# one-electron
for j,st in enumerate(dets):
    for a in range(N):
        for b in range(N):
            ma,sa=orbs[a]; mb,sb=orbs[b]
            if sa!=sb: continue
            h=scale*W[ms.index(ma),ms.index(mb)]
            if h==0: continue
            r=apply_ann(st,b)
            if r is None: continue
            s1,st1=r
            r=apply_cre(st1,a)
            if r is None: continue
            s2,st2=r
            H[idx[st2],j]+=h*s1*s2
# two-electron
for j,st in enumerate(dets):
    for a in range(N):
     for b in range(N):
      for c in range(N):
       for d in range(N):
        v=Vt[a,b,c,d]
        if v==0: continue
        r=op2(st,a,b,c,d)
        if r is None: continue
        s,st2=r
        H[idx[st2],j]+=0.5*v*s
# S^2 = Sz^2 + (S+S- + S-S+)/2 ; S+ = sum_m a+_{m,up} a_{m,down}
def Splus(vec):
    out=np.zeros(D)
    for j,st in enumerate(dets):
        if vec[j]==0: continue
        for m in ms:
            up=orbs.index((m,1)); dn=orbs.index((m,-1))
            r=apply_ann(st,dn)
            if r is None: continue
            s1,st1=r
            r=apply_cre(st1,up)
            if r is None: continue
            s2,st2=r
            out[idx[st2]]+=vec[j]*s1*s2
    return out
def Sminus_mat():
    M=np.zeros((D,D))
    for j,st in enumerate(dets):
        for m in ms:
            up=orbs.index((m,1)); dn=orbs.index((m,-1))
            r=apply_ann(st,up)
            if r is None: continue
            s1,st1=r
            r=apply_cre(st1,dn)
            if r is None: continue
            s2,st2=r
            M[idx[st2],j]+=s1*s2
    return M
Sm=Sminus_mat(); Sp=Sm.T
Sz=np.zeros(D)
for j,st in enumerate(dets):
    Sz[j]=0.5*sum(1 if orbs[x][1]==1 else -1 for x in st)
S2=np.diag(Sz**2)+0.5*(Sp@Sm+Sm@Sp)
# high-spin check
s2e,U=np.linalg.eigh(S2)
def subspace(S):
    sel=U[:,np.abs(s2e-S*(S+1))<1e-6]
    return sel
def lowest(Sval,Dq_):
    return None
# Build H(Dq) and get lowest doublet and sextet energies
def energies(Dq_):
    global H
    return None
# Store Hee and one-electron separately
Hee=H.copy()
# re-make one-electron: H = Hee + Dq*Hcf  where Hcf built from W scaled by 1? (already included scale*W*Dq below)
Hcf=np.zeros((D,D))
for j,st in enumerate(dets):
    for a in range(N):
        for b in range(N):
            ma,sa=orbs[a]; mb,sb=orbs[b]
            if sa!=sb: continue
            h=W[ms.index(ma),ms.index(mb)]
            if h==0: continue
            r=apply_ann(st,b)
            if r is None: continue
            s1,st1=r
            r=apply_cre(st1,a)
            if r is None: continue
            s2,st2=r
            Hcf[idx[st2],j]+=h*s1*s2
Hcf*=scale
# Coulomb-only part
Hee_only=Hee - Hcf*0  # placeholder
# recompute Coulomb-only: Hee currently contains only 2e terms? (H built with one-electron term at Dq=0 earlier)
EOF
echo done