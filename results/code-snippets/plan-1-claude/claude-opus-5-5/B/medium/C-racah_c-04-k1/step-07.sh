cd /tmp/tsbench-home-xehwqch9; python3 - << 'EOF' 2>&1 | tail -20
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ms=[-2,-1,0,1,2]
CK={}
def ck(k,m,mp):
    if abs(m-mp)>k: return 0.0
    key=(k,m,mp)
    if key not in CK: CK[key]=float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
    return CK[key]
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def g(a,b,c,d,F2,F4):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[x] for x in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F for k,F in ((2,F2),(4,F4)))
def build(F2,F4,Dq):
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={2:1,1:-4,0:6}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets); Hm=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[ms.index(orbs[q][0]),ms.index(orbs[p][0])]
                if v==0 or (q!=p and q in d): continue
                occ=list(d); sign=1
                i=occ.index(p); sign*=(-1)**i; occ.pop(i)
                i=sum(1 for y in occ if y<q); sign*=(-1)**i; occ.insert(i,q)
                Hm[idx[tuple(occ)],I]+=sign*v
        for p,q in itertools.combinations(d,2):
            for r in range(10):
                for s in range(10):
                    rest=[x for x in d if x not in (p,q)]
                    if r==s or r in rest or s in rest: continue
                    val=g(r,s,p,q,F2,F4)-g(r,s,q,p,F2,F4)
                    if val==0: continue
                    occ=list(d); sign=1
                    for x in (p,q):
                        i=occ.index(x); sign*=(-1)**i; occ.pop(i)
                    for x in (s,r):
                        i=sum(1 for y in occ if y<x); sign*=(-1)**i; occ.insert(i,x)
                    Hm[idx[tuple(occ)],I]+=0.5*sign*val
    return Hm
HB=build(49,0,0); HC=build(49*5/35,441/35,0); HD=build(0,0,1)
def lev(Dq,B,C):
    e=np.linalg.eigvalsh(B*HB+C*HC+Dq*HD); return np.unique(np.round(e-e[0],1))
print(lev(0,1000,4000)[:6])
print(lev(1743,781,3000)[:8])
from scipy.optimize import brentq, least_squares
f=lambda C: lev(1743,781,C)[1]-15410
C=brentq(f,500,8000); print(C, C/781, lev(1743,781,C)[:10])
# full fit: identify quartet bands via spin: use S^2? simpler: quartets independent of C
def quart(Dq,B):
    a=lev(Dq,B,0); b=lev(Dq,B,1000)
    return sorted(set(a)&set(b))
print(quart(1743,781)[:4])
EOF