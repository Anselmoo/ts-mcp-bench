import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
# ck
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# two-electron integrals <ab|cd> spatial
def g(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
# crystal field in real basis: oct, cubic harmonic; in complex m basis: V(0)=6Dq, V(+-1)=-4Dq,V(+-2)=Dq, <2|V|-2>=5Dq
def cf(Dq):
    V=np.zeros((5,5))
    d={-2:Dq,-1:-4*Dq,0:6*Dq,1:-4*Dq,2:Dq}
    for m in ms: V[m+2,m+2]=d[m]
    V[0,4]=V[4,0]=5*Dq
    return V
def H(Dq,B,C):
    F4=C/35; F2=B+5*F4
    F={0:0,2:F2*49,4:F4*441}
    V=cf(Dq)
    Hm=np.zeros((N,N))
    for i,D in enumerate(dets):
        # one-body
        for p in D:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                if q!=p and q in D: continue
                L=list(D); pos=L.index(p); L[pos]=q
                sign=(-1)**sum(1 for x in L if x<q)*(-1)**sum(1 for x in D if x<p)
                # simpler: annihilate p then create q
                rem=[x for x in D if x!=p]
                s=(-1)**D.index(p)*(-1)**sum(1 for x in rem if x<q)
                new=tuple(sorted(rem+[q]))
                Hm[idx[new],i]+=s*v
        # two-body
        for a_,b_ in itertools.combinations(D,2):
            rem=[x for x in D if x not in (a_,b_)]
            s1=(-1)**D.index(a_)*(-1)**([x for x in D if x!=a_].index(b_))
            for c_ in range(10):
                for d_ in range(10):
                    if c_==d_ or c_ in rem or d_ in rem: continue
                    oa,ob,oc,od=orbs[a_],orbs[b_],orbs[c_],orbs[d_]
                    val=0
                    if oa[1]==oc[1] and ob[1]==od[1]: val+=g(oc[0],od[0],oa[0],ob[0],F)
                    if oa[1]==od[1] and ob[1]==oc[1]: val-=g(oc[0],od[0],ob[0],oa[0],F)
                    if val==0: continue
                    # create d then c: c† d† b a
                    r2=sorted(rem+[d_]); s2=(-1)**sum(1 for x in rem if x<d_)
                    s3=(-1)**sum(1 for x in r2 if x<c_)
                    new=tuple(sorted(r2+[c_]))
                    Hm[idx[new],i]+=0.5*val*s1*s2*s3
    return Hm
# Note pairs counted once with antisym both orders -> factor
import pickle
def levels(Dq,B,C):
    Hm=H(Dq,B,C)
    w,v=np.linalg.eigh(Hm)
    # S^2
    return w,v
