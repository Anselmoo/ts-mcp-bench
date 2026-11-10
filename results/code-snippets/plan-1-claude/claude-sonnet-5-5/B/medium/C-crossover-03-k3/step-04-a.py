import numpy as np, itertools, functools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=803.;C=3078.
Fk={2:49*B+7*C,4:63*C/5}
@functools.lru_cache(None)
def c(k,m,mp):
    return float((-1)**m*2*gaunt(2,k,2,-m,m-mp,mp)) if abs(m-mp)<=k else 0.0
orb=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
n=10
V={}
for a in range(n):
 for b in range(n):
  for cc in range(n):
   for d in range(n):
    ma,sa=orb[a];mb,sb=orb[b];mc,sc=orb[cc];md,sd=orb[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    v=sum(Fk[k]*c(k,ma,mc)*c(k,md,mb) for k in (2,4))
    if abs(v)>1e-9: V[(a,b,cc,d)]=v
def hcf(Dq):
    h=np.zeros((10,10))
    for s in (0.5,-0.5):
        i=lambda m:orb.index((m,s))
        h[i(2),i(2)]=Dq;h[i(-2),i(-2)]=Dq;h[i(2),i(-2)]=h[i(-2),i(2)]=5*Dq
        h[i(0),i(0)]=6*Dq;h[i(1),i(1)]=-4*Dq;h[i(-1),i(-1)]=-4*Dq
    return h
dets=list(itertools.combinations(range(n),6))
def apply(det,ops):
    l=list(det);sign=1
    for typ,i in ops:
        if typ=='a':
            if i not in l: return 0,None
            p=l.index(i);sign*=(-1)**p;l.pop(p)
        else:
            if i in l: return 0,None
            p=sum(1 for x in l if x<i);sign*=(-1)**p;l.insert(p,i)
    return sign,tuple(l)
def build(sel,Dq):
    ix={d:i for i,d in enumerate(sel)}
    N=len(sel);H=np.zeros((N,N));S2=np.zeros((N,N));h=hcf(Dq)
    for det in sel:
        j=ix[det]
        for a in range(n):
         for b in range(n):
          if h[a,b]!=0:
            s,nd=apply(det,[('a',b),('c',a)])
            if s and nd in ix: H[ix[nd],j]+=s*h[a,b]
        for (a,b,cc,d),v in V.items():
            s,nd=apply(det,[('a',cc),('a',d),('c',b),('c',a)])
            if s and nd in ix: H[ix[nd],j]+=0.5*s*v
        sz=sum(orb[i][1] for i in det);S2[j,j]+=sz*sz+sz
        for m in range(-2,3):
            for m2 in range(-2,3):
                up=orb.index((m,.5));dn=orb.index((m,-.5));up2=orb.index((m2,.5));dn2=orb.index((m2,-.5))
                s,nd=apply(det,[('a',dn2),('c',up2),('a',up),('c',dn)])
                if s and nd in ix: S2[ix[nd],j]+=s
    return H,S2
sel0=[d for d in dets if sum(orb[i][1] for i in d)==0]
sel2=[d for d in dets if sum(orb[i][1] for i in d)==2]
def gap(Dq):
    H0,S=build(sel0,Dq)
    e0=np.linalg.eigvalsh(H0+1e6*S)[0]
    H5,_=build(sel2,Dq)
    return e0-np.linalg.eigvalsh(H5)[0]
for D in (1000,1500,2000):print(D,gap(D))
print(brentq(gap,800,3000,xtol=0.01))
