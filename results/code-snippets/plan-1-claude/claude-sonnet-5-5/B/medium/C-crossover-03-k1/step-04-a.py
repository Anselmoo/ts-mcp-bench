import numpy as np, itertools, functools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=803.;C=3078.
F={0:0,2:49*B+7*C,4:63*C/5}
orb=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
@functools.lru_cache(None)
def c(k,m1,m2):
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2))
def V(a,b,cc,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cc,d
    if s1!=s3 or s2!=s4 or m1-m3!=m4-m2: return 0
    return sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
dets=[d for d in itertools.combinations(range(10),6) if sum(orb[i][1] for i in d)==0]
idx={d:i for i,d in enumerate(dets)};n=len(dets)
def ac(det,ops):
    d=list(det);sg=1
    for t,p in ops:
        if t=='a':
            if p not in d:return None,0
            k=d.index(p);sg*=(-1)**k;d.pop(k)
        else:
            if p in d:return None,0
            k=sum(1 for x in d if x<p);sg*=(-1)**k;d.insert(k,p)
    return tuple(d),sg
def h1(Dq):
    e1=np.zeros(5);e1[2]=1
    e2=np.zeros(5);e2[0]=e2[4]=2**-.5
    Pe=np.outer(e1,e1)+np.outer(e2,e2)
    h=6*Dq*Pe-4*Dq*(np.eye(5)-Pe)
    H=np.zeros((10,10))
    for i,(m,s) in enumerate(orb):
        for j,(k,t) in enumerate(orb):
            if s==t:H[i,j]=h[m+2,k+2]
    return H
def build1(Dq):
    h=h1(Dq);H=np.zeros((n,n))
    for det in dets:
        j=idx[det]
        for p in range(10):
            for q in range(10):
                if h[p,q]!=0:
                    nd,s=ac(det,[('a',q),('c',p)])
                    if nd in idx:H[idx[nd],j]+=s*h[p,q]
    return H
HV=np.zeros((n,n))
Vl=[(p,q,r,s,V(orb[p],orb[q],orb[r],orb[s])) for p in range(10) for q in range(10) for r in range(10) for s in range(10)]
Vl=[x for x in Vl if x[4]!=0]
for det in dets:
    j=idx[det]
    for p,q,r,s,v in Vl:
        nd,sg=ac(det,[('a',s),('a',r),('c',q),('c',p)])
        if nd in idx:HV[idx[nd],j]+=0.5*sg*v
S2=np.zeros((n,n))
for det in dets:
    j=idx[det]
    for i,(m,s) in enumerate(orb):
        if s==-0.5:
            d1,c1=ac(det,[('a',i),('c',i-1)])
            if d1:
                for k,(m2,s2) in enumerate(orb):
                    if s2==0.5:
                        d2,c2=ac(d1,[('a',k),('c',k+1)])
                        if d2 in idx:S2[idx[d2],j]+=c1*c2
w,v=np.linalg.eigh((S2+S2.T)/2)
def gs(Dq,S):
    sel=v[:,abs(w-S*(S+1))<1e-6]
    return np.linalg.eigvalsh(sel.T@(HV+build1(Dq))@sel).min()
f=lambda D:gs(D,2)-gs(D,0)
for D in (1000,1500,2000,2500,3000):print(D,f(D))
print(brentq(f,1000,3500))
