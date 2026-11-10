cd /dev/shm && cat << 'EOF' > d3.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ms=[-2,-1,0,1,2]
def c(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def ann(det,q):
    if q not in det: return None
    i=det.index(q); return det[:i]+det[i+1:], (-1)**i
def cre(det,p):
    if p in det: return None
    n=sum(1 for x in det if x<p); return tuple(sorted(det+(p,))), (-1)**n
def ops(det,seq):
    s=1
    for t,o in reversed(seq):
        r=ann(det,o) if t=='a' else cre(det,o)
        if r is None: return None
        det,x=r; s*=x
    return det,s
CC={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
N=len(dets)
# precompute unit matrices
def mat_1(V):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V[ms.index(so[p][0]),ms.index(so[q][0])]
                if v==0: continue
                r=ops(d,[('c',p),('a',q)])
                if r: H[idx[r[0]],I]+=v*r[1]
    return H
def mat_2(k):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p,q,r_,s in itertools.product(range(10),repeat=4):
            (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[p],so[q],so[r_],so[s]
            if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
            val=CC[(k,ma,mc)]*CC[(k,md,mb)]
            if abs(val)<1e-12: continue
            r=ops(d,[('c',p),('c',q),('a',s),('a',r_)])
            if r: H[idx[r[0]],I]+=0.5*val*r[1]
    return H
V=np.zeros((5,5))
for i,m in enumerate(ms): V[i,i]={2:1,-2:1,1:-4,-1:-4,0:6}[m]
V[0,4]=V[4,0]=5
HV=mat_1(V); H2=mat_2(2); H4=mat_2(4)
np.savez('m.npz',HV=HV,H2=H2,H4=H4)
EOF
python3 d3.py && echo done