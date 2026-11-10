import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from math import sqrt,pi
def c(k,m1,m3):
    # c^k(l m1; l m3) = sqrt(4pi/(2k+1)) * int Y*_{2m1} Y_{k,m1-m3} Y_{2m3}
    q=m1-m3
    if abs(q)>k: return 0.0
    return float((-1)**m1*sqrt(4*pi/(2*k+1))*gaunt(2,k,2,-m1,q,m3))
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]
C={(k,a,b):c(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def build(B,Cc,Dq):
    F={0:0,2:49*B+7*Cc,4:63*Cc/5}
    dets=[d for d in itertools.combinations(range(10),4) if sum(so[i][1] for i in d)==2]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets);H=np.zeros((n,n));S2=np.zeros((n,n))
    vd={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}
    def V(i,j,k,l): # <ij|kl> orbitals i,j -> k,l : electron1 i->k, electron2 j->l
        (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k],so[l]
        if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
        return sum(C[(kk,m1,m3)]*C[(kk,m4,m2)]*F[kk] for kk in (2,4)) # F0 dropped
    def apply_ops(d):
        pass
    for d in dets:
        a=idx[d]
        # one-body
        for p in d:
            m,s=so[p]
            H[a,a]+=vd[m]
            if False:pass
        # two-body diag and offdiag: general via loops over occupied pairs and target orbitals
        for (p,q) in itertools.combinations(d,2):
            rest=[x for x in d if x not in(p,q)]
            for r in range(10):
                for t in range(10):
                    if r==t or r in rest or t in rest: continue
                    # H = 1/2 sum <ij|kl> a+i a+j a_l a_k ; pair (p,q) annihilated, create r,t
                    amp=0
                    # sum over ordered assignments
                    for (k,l) in((p,q),(q,p)):
                        val=V(r,t,k,l)
                        if val==0: continue
                        # sign: state = a+r a+t a_l a_k |d> with ordering
                        amp+=val*sgn(d,k,l,r,t)
                    if amp!=0:
                        newd=tuple(sorted(rest+[r,t]))
                        H[idx[newd],a]+=0.5*amp
        # S2 = S-S+ + Sz(Sz+1): Sz=2... use S^2 = S-S+ + Sz^2+Sz
    # S2 via spin ops
    def Sp(d):
        out={}
        for p in d:
            m,s=so[p]
            if s==-1:
                q=so.index((m,1))
                if q in d: continue
                nd=[x for x in d];pos=nd.index(p);nd[pos]=q
                # sign from reordering
                srt=sorted(nd);sg=perm_sign(nd)
                out[tuple(srt)]=out.get(tuple(srt),0)+sg
        return out
    def Sm(d):
        out={}
        for p in d:
            m,s=so[p]
            if s==1:
                q=so.index((m,-1))
                if q in d: continue
                nd=list(d);pos=nd.index(p);nd[pos]=q
                out[tuple(sorted(nd))]=out.get(tuple(sorted(nd)),0)+perm_sign(nd)
        return out
    for d in dets:
        a=idx[d]
        S2[a,a]+=2*2+2*0+0
        # Sz=1 here: Sz^2+Sz=2 ; S-S+... need Sm Sp on Ms=1 -> Sp gives Ms=2 dets (not in list)
    return dets,idx,H,S2
def perm_sign(l):
    l=list(l);s=1
    for i in range(len(l)):
        for j in range(i+1,len(l)):
            if l[i]>l[j]: s=-s
    return s
def sgn(d,k,l,r,t):
    # apply a_k then a_l then a+t then a+r? using op order a+r a+t a_l a_k (a_k first)
    occ=list(d)
    def ann(occ,x):
        i=occ.index(x);return occ[:i]+occ[i+1:],(-1)**i
    def cre(occ,x):
        # a+ x on front: ordered list convention: put at front then sort sign
        return [x]+occ,1
    o,s1=ann(occ,k);o,s2=ann(o,l);o,s3=cre(o,t);o,s4=cre(o,r)
    return s1*s2*s3*s4*perm_sign(o)
