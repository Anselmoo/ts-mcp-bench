
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
# c^k
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0) 
from sympy.physics.wigner import wigner_3j
def cK(k,ma,mb):
    return float((-1)**ma*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-ma,ma-mb,mb))
# two-electron integral <ab|cd> spatial with m
def R(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(cK(k,a,c)*cK(k,d,b)*F[k] for k in (0,2,4))
# crystal field in real basis -> complex: Oh Dq: <m|V|m'>
def Vcf(Dq):
    V=np.zeros((5,5))
    idx=lambda m:m+2
    V[idx(0),idx(0)]=6*Dq
    for m in (1,-1): V[idx(m),idx(m)]=-4*Dq
    for m in (2,-2): V[idx(m),idx(m)]=Dq
    V[idx(2),idx(-2)]=V[idx(-2),idx(2)]=5*Dq
    return V
dets=list(itertools.combinations(range(10),5))
di={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    n=len(dets);Hm=np.zeros((n,n))
    V=Vcf(Dq)
    # one-body
    for i,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if orbs[q][1]!=orbs[p][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); nd[nd.index(p)]=q
                sign=1
                # sort
                perm=np.argsort(nd); sd=tuple(sorted(nd))
                # parity
                arr=list(nd);s=1
                for a in range(len(arr)):
                    for b in range(a+1,len(arr)):
                        if arr[a]>arr[b]: s=-s
                Hm[di[sd],i]+=s*v
    # two-body: sum_{p<q, r<s} (<rs|pq>-<rs|qp>) a+r a+s a q a p
    for i,d in enumerate(dets):
        for pi_,qi_ in itertools.combinations(range(5),2):
            p,q=d[pi_],d[qi_]
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s_ in range(r+1,10):
                    if (r in rest) or (s_ in rest): continue
                    def g(a,b,c,dd):
                        if orbs[a][1]!=orbs[c][1] or orbs[b][1]!=orbs[dd][1]: return 0
                        return R(orbs[a][0],orbs[b][0],orbs[c][0],orbs[dd][0],F)
                    val=g(r,s_,p,q)-g(r,s_,q,p)
                    if abs(val)<1e-12: continue
                    # state: remove p,q, add r,s. sign via ordered list
                    lst=list(d)
                    # annihilate q then p: a_s... do via list ops
                    sg=1
                    k=lst.index(q); sg*=(-1)**k; lst.pop(k)
                    k=lst.index(p); sg*=(-1)**k; lst.pop(k)
                    # create s then r: a+r a+s |>
                    import bisect
                    k=bisect.bisect(lst,s_); sg*=(-1)**k; lst.insert(k,s_)
                    k=bisect.bisect(lst,r); sg*=(-1)**k; lst.insert(k,r)
                    Hm[di[tuple(lst)],i]+=sg*val
    return Hm
# S^2
def S2():
    n=len(dets);M=np.zeros((n,n))
    for i,d in enumerate(dets):
        ms=sum(0.5 if orbs[x][1]==0 else -0.5 for x in d)
        M[i,i]+=ms*ms-ms  # S+S- = S^2 - Sz^2 + Sz -> S^2=S-S+ + Sz^2+Sz ; use S-S+
        M[i,i]+=2*ms
        # S-S+ : diag part
    return None
import pickle
EOF
echo ok