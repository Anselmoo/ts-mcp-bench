
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
ms=[-2,-1,0,1,2]
# ck coefficients
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
# two-electron integral <ab|1/r|cd> in terms of F0,F2,F4
def g(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (0,2,4))
# crystal field octahedral in real basis: one-electron matrix in complex m
def cf(Dq):
    h=np.zeros((5,5))
    # V = Dq*(6 for m=0, -4 for m=±1, 1 for m=±2) diag, plus 5Dq coupling m=±2 
    d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): h[i,i]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
def H(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    h1=cf(Dq)
    N=len(dets);M=np.zeros((N,N))
    for I,D in enumerate(dets):
        for J,E in enumerate(dets):
            val=0
            # brute force via second quantization
            pass
    return M
# simpler: use operator approach
def apply_one(i,j,det):  # a_i^+ a_j
    det=list(det)
    if j not in det: return None
    p=det.index(j); sign=(-1)**p; det.pop(p)
    if i in det: return None
    det.append(i); 
    # sort with sign
    arr=det[:]; s=1
    for x in range(len(arr)):
        for y in range(len(arr)-1-x):
            if arr[y]>arr[y+1]: arr[y],arr[y+1]=arr[y+1],arr[y]; s=-s
    # a_i^+ placed at front: our append at end, need sign for moving to front
    s*= (-1)**(len(det)-1)
    return tuple(arr),sign*s
def Hmat(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    h=cf(Dq); N=len(dets); M=np.zeros((N,N))
    for J,D in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if orbs[a][1]!=orbs[b][1]: continue
                v=h[orbs[a][0]+2,orbs[b][0]+2]
                if v==0: continue
                r=apply_one(a,b,D)
                if r: M[idx[r[0]],J]+=v*r[1]
        # two body: 1/2 sum g(abcd) a+ b+ d c
        for cc in D:
            for d in D:
                if cc==d: continue
                for a in range(10):
                    for b in range(10):
                        v=g(a,b,cc,d,F)
                        if v==0: continue
                        r1=apply_one(b,d,D) # a_b^+ a_d
                        if not r1: continue
                        r2=apply_one(a,cc,r1[0])
                        if not r2: continue
                        M[idx[r2[0]],J]+=0.5*v*r1[1]*r2[1]
    return M
import sys
Dq,B=1417,878
def levels(C):
    e=np.linalg.eigvalsh(Hmat(Dq,B,C)); e=np.round(e-e[0],1)
    return sorted(set(e))
print(levels(4*B)[:8])
def f(C):
    return levels(C)[1]-18540
Cs=brentq(f,2*B,6*B,xtol=0.5); print(Cs,Cs/B,levels(Cs)[:6])
EOF
python3 /tmp/d3.py
