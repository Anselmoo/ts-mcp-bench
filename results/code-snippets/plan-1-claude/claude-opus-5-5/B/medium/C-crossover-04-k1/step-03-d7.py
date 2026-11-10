import numpy as np, itertools, math
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
B,C=922.,4156.
f4=C/35; f2=B+5*f4
Fk={0:0.0,2:f2*49,4:f4*441}
ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
def ckf(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ckf(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def g(a,b,c,d):
    if a+b!=c+d: return 0.
    return sum(CK[(k,a,c)]*CK[(k,d,b)]*Fk[k] for k in (0,2,4))
V=np.zeros((5,5)); idx={m:i for i,m in enumerate(ml)}
V[idx[0],idx[0]]=6; V[idx[1],idx[1]]=-4; V[idx[-1],idx[-1]]=-4
V[idx[2],idx[2]]=1; V[idx[-2],idx[-2]]=1; V[idx[2],idx[-2]]=5; V[idx[-2],idx[2]]=5
n=7
basis=[b for b in itertools.combinations(range(10),n) if sum(1 if orbs[o][1] else -1 for o in b)==1]
bi={b:i for i,b in enumerate(basis)}; N=len(basis)
def apply(det,rem,add):
    d=list(det); s=1
    for r in rem:
        if r not in d: return 0,None
        p=d.index(r); s*=(-1)**p; d.pop(p)
    for a in reversed(add):
        if a in d: return 0,None
        d.insert(0,a)
    for i in range(len(d)):
        for j in range(len(d)-1-i):
            if d[j]>d[j+1]: d[j],d[j+1]=d[j+1],d[j]; s=-s
    return s,tuple(d)
H1=np.zeros((N,N)); H2=np.zeros((N,N)); S2=np.zeros((N,N))
for i,det in enumerate(basis):
    for p in det:
        for q in range(10):
            if orbs[p][1]!=orbs[q][1]: continue
            v=V[idx[orbs[q][0]],idx[orbs[p][0]]]
            if v==0: continue
            s,nd=apply(det,[p],[q])
            if s: H1[bi[nd],i]+=s*v
    for p1,p2 in itertools.combinations(det,2):
        for q1 in range(10):
            for q2 in range(10):
                if q1==q2: continue
                m1,s1=orbs[p1];m2,s2=orbs[p2];n1,t1=orbs[q1];n2,t2=orbs[q2]
                if s1!=t1 or s2!=t2: continue
                v=g(n1,n2,m1,m2)
                if v==0: continue
                s,nd=apply(det,[p2,p1],[q1,q2])
                if s: H2[bi[nd],i]+=s*v
    # S^2 = S-S+ + Sz^2+Sz, Sz=1/2
    S2[i,i]+=0.75
    for a in range(10):
        if orbs[a][1]!=0: continue
        for b in range(10):
            if orbs[b][1]!=1 or orbs[b][0]!=orbs[a][0]: continue
            # S+ : a(down)->a'(up); then S-: b(up)->b'(down)
            s1,d1=apply(det,[a],[a+1])
            if not s1: continue
            s2,d2=apply(d1,[b],[b-1])
            if s2 and d2 in bi: S2[bi[d2],i]+=s1*s2
def lev(Dq):
    w,v=np.linalg.eigh(H2+Dq*H1)
    s=np.einsum('ij,ik,kj->j',v,S2,v)
    e4=w[np.isclose(s,3.75,atol=1e-3)].min(); e2=w[np.isclose(s,0.75,atol=1e-3)].min()
    return e2-e4
Dq=brentq(lev,300,5000,xtol=1e-6); print(Dq, Dq/B)
