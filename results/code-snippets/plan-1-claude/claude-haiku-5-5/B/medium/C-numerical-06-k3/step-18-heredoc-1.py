import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import lru_cache
from scipy.optimize import brentq
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3): return float(gaunt(l1,l2,l3,m1,m2,m3))
def Ang(k,oa,oc,ob,od):
    ma,mc,mb,md=oa-2,oc-2,ob-2,od-2; tot=0.0
    for q in range(-k,k+1):
        g1=G(2,k,2,-ma,-q,mc)
        if g1==0: continue
        g2=G(2,k,2,-mb,q,md)
        if g2==0: continue
        tot+=(-1)**(q%2)*(-1)**ma*g1*(-1)**mb*g2*(4*pi/(2*k+1))
    return tot
def build(Fk):
    N=10; V=np.zeros((N,N,N,N))
    for oa,ob,oc,od in itertools.product(range(5),repeat=4):
        val=sum(Fk[k]*Ang(k,oa,oc,ob,od) for k in (0,2,4))
        if abs(val)<1e-12: continue
        for sa,sb in itertools.product(range(2),repeat=2):
            V[2*oa+sa,2*ob+sb,2*oc+sa,2*od+sb]=val
    return V
N=10
dets=[d for d in itertools.combinations(range(N),7) if sum(1 for s in d if s%2==0)==5]
idx={d:i for i,d in enumerate(dets)}
M=len(dets)
def ap(ops,det):
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(occ)
def Hmat(V):
    H=np.zeros((M,M))
    nz=[(a,b,c,d,V[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if V[a,b,c,d]!=0]
    for j,dj in enumerate(dets):
        for a,b,c,d,v in nz:
            r=ap([('a',c),('a',d),('c',b),('c',a)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H[idx[nd],j]+=0.5*s*v
    return H
H2=Hmat(build({0:0,2:1.0,4:0})); H4=Hmat(build({0:0,2:0,4:1.0}))
s2=sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
h5=np.zeros((5,5),complex)
for v,e in [(vec({2:1/(1j*s2),-2:-1/(1j*s2)}),-4),(vec({1:-1/s2,-1:1/s2}),-4),(vec({1:1j/s2,-1:1j/s2}),-4),(vec({0:1}),6),(vec({2:1/s2,-2:1/s2}),6)]:
    h5+=e*np.outer(v,v.conj())
h=np.zeros((N,N),complex)
for o1 in range(5):
    for o2 in range(5):
        for sg in range(2): h[2*o1+sg,2*o2+sg]=h5[o1,o2]
H1=np.zeros((M,M))
for j,dj in enumerate(dets):
    for a in range(N):
        for c in range(N):
            if abs(h[a,c])<1e-14: continue
            r=ap([('a',c),('c',a)],dj)
            if r is None: continue
            s,nd=r
            if nd in idx: H1[idx[nd],j]+=s*h[a,c].real
C=4.0; F4=441*C/35; F2=(441*1.0+5*F4)/9
def levels(x):
    ev=np.linalg.eigvalsh(x*H1+F2*H2+F4*H4)
    g=[]
    for e in ev:
        if g and abs(e-g[-1][0])<1e-6: g[-1][1]+=1
        else: g.append([e,1])
    return [a-g[0][0] for a,_ in g[1:]], [b for _,b in g]
# scan: nu1 (3-fold T2g), then the two next levels
target_r2=19550/9180; target_r3=20320/9180
for x in np.arange(0.9,1.6,0.05):
    nu,deg=levels(x)
    print(round(x,3), np.round(np.array(nu)/nu[0],4), deg)
