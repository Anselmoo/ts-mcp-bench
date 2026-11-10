import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
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
def ops(det,seq):  # seq applied right to left: list of ('a'/'c',orb)
    s=1
    for t,o in reversed(seq):
        r=ann(det,o) if t=='a' else cre(det,o)
        if r is None: return None
        det,x=r; s*=x
    return det,s
def build(Dq,B,Cr):
    F={0:0,2:49*B+7*Cr,4:441*Cr/35}
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}[m]
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V[ms.index(so[p][0]),ms.index(so[q][0])]
                if v==0: continue
                r=ops(d,[('c',p),('a',q)])
                if r: H[idx[r[0]],I]+=v*r[1]
        for p,q,r_,s in itertools.product(range(10),repeat=4):
            (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[p],so[q],so[r_],so[s]
            if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
            val=sum(F[k]*c(k,ma,mc)*c(k,md,mb) for k in (2,4)) if False else None
            val=sum(F[k]*CC[(k,ma,mc)]*CC[(k,md,mb)] for k in (2,4))
            if abs(val)<1e-12: continue
            r=ops(d,[('c',p),('c',q),('a',s),('a',r_)])
            if r: H[idx[r[0]],I]+=0.5*val*r[1]
    return H
CC={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
def levels(Dq,B,Cr):
    e=np.linalg.eigvalsh(build(Dq,B,Cr)); e=e-e[0]
    u=[];
    for x in np.round(e,3):
        if not u or abs(x-u[-1][0])>0.5: u.append([x,1])
        else: u[-1][1]+=1
    return u
print(levels(1917,824,3296)[:8])
