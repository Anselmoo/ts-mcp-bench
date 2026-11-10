cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    if abs(m-mp)>k: return 0.0
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def g(a,b,c,d,F2,F4):
    # <ab|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[x] for x in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F for k,F in ((2,F2),(4,F4)))
def H(Dq,B,C):
    F4=C/35.; F2=B+5*F4
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={2:1,1:-4,0:6}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets); Hm=np.zeros((N,N))
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[ms.index(orbs[q][0]),ms.index(orbs[p][0])]
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); pos=nd.index(p); nd[pos]=q
                sign=1; 
                # sort with sign
                arr=nd[:]
                for i in range(3):
                    for j in range(2-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                Hm[idx[tuple(arr)],I]+=sign*v
        # two-body
        for p,q in itertools.combinations(d,2):
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    rest=[x for x in d if x not in (p,q)]
                    if r in rest or s in rest: continue
                    val=g(r,s,p,q,F2,F4)-g(r,s,q,p,F2,F4)
                    if val==0: continue
                    # annihilate q,p then create s? use a_r^+ a_s^+ a_q a_p /2 ... do explicit ordering
                    # state: ordered d. apply a_p a_q then... simpler: build occupation and compute sign
                    occ=list(d)
                    sign=1
                    # a_q a_p |d> with operator order a_r^+ a_s^+ a_q a_p (sum over p<q pairs, r!=s both orders, factor 1/2 * with antisym gives val over r,s ordered pairs/2)
                    for x in (p,q):
                        i=occ.index(x); sign*= (-1)**i; occ.pop(i)
                    for x in (s,r):
                        i=sum(1 for y in occ if y<x); sign*=(-1)**i; occ.insert(i,x)
                    Hm[idx[tuple(occ)],I]+=0.5*sign*val
    return Hm
def lev(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); e=e-e[0]
    return e
e=lev(1743,781,3000); print(np.round(np.unique(np.round(e,1)),1)[:12])
EOF
python3 /tmp/d3.py