
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2
# Slater: F0,F2,F4 ; B=(F2/49 - 5F4/441), C=35F4/441
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy.physics.wigner import wigner_3j
def c(k,ma,mb):
    return float((-1)**ma*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-ma,ma-mb,mb))
cache={}
def V(a,b,cc,d,F):
    # <ab|1/r|cd>, a,c electron1
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*c(k,ma,mc)*c(k,md,mb) for k in (0,2,4))
# crystal field octahedral in real basis: eg energy 6Dq, t2g -4Dq; in complex m basis
def hcf(Dq):
    h=np.zeros((5,5))
    # V = Dq*(... ) : diag m=0:6, ±1:-4, ±2:1 ; <2|V|-2>=5
    d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): h[i,i]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def build(Dq,B,C):
    F4=C*441/35; F2=49*(B+5*F4/441); F=[0,0,F2,0,F4]
    F={0:0,2:F2,4:F4}
    h1=hcf(Dq)
    H=np.zeros((N,N))
    for I,D in enumerate(dets):
        Ds=list(D)
        # one-body
        for p in Ds:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=h1[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                if q!=p and q in Ds: continue
                new=Ds.copy(); pos=new.index(p); new[pos]=q
                sign=(-1)**sum(1 for i in range(len(new)) for j in range(i+1,len(new)) if new[i]>new[j])
                H[idx[tuple(sorted(new))],I]+=sign*v
        # two-body
        for i1 in range(6):
            for i2 in range(i1+1,6):
                p,q=Ds[i1],Ds[i2]
                for r in range(10):
                    for s in range(10):
                        if r>=s: continue
                        rest=[x for x in Ds if x not in(p,q)]
                        if r in rest or s in rest: continue
                        v=V(r,s,p,q,F)-V(r,s,q,p,F)
                        if abs(v)<1e-12: continue
                        new=Ds.copy(); new[i1]=r; new[i2]=s
                        sign=(-1)**sum(1 for i in range(6) for j in range(i+1,6) if new[i]>new[j])
                        H[idx[tuple(sorted(new))],I]+=sign*v
    return H
# S^2 to identify singlets
def Ms(D): return sum(0.5 if orbs[p][1]==0 else -0.5 for p in D)
import pickle
# precompute Hcf unit, B unit, C unit since linear
H_D=build(1,0,0); H_B=build(0,1,0); H_C=build(0,0,1)
# S^2
S2=np.zeros((N,N))
for I,D in enumerate(dets):
    Ds=list(D)
    S2[I,I]+=Ms(D)**2
    # S+S-: S2 = S-S+ + Sz^2 + Sz
    S2[I,I]+=Ms(D)
    for p in Ds:
        if orbs[p][1]==1:
            q=p-1
            if q in Ds: continue
            new=Ds.copy(); new[new.index(p)]=q
            sp=(-1)**sum(1 for i in range(6) for j in range(i+1,6) if new[i]>new[j])
            # apply S- after
            for p2 in new:
                if orbs[p2][1]==0:
                    q2=p2+1
                    if q2 in new and q2!=p2: 
                        continue
                    n2=new.copy(); n2[n2.index(p2)]=q2
                    sm=(-1)**sum(1 for i in range(6) for j in range(i+1,6) if n2[i]>n2[j])
                    S2[idx[tuple(sorted(n2))],I]+=sp*sm
np.save('/tmp/H.npy',np.array([H_D,H_B,H_C,S2]))
EOF
python3 /tmp/d6.py && echo ok