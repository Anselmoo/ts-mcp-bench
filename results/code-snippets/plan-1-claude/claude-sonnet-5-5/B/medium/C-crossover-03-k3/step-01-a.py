import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=803.;C=3078.
F2=49*B+7*C;F4=63*C/5
def ck(k,l,m,lp,mp): # <l m|C^k|l' m'> 
    return float((-1)**m*np.sqrt((2*l+1)*(2*lp+1))*gaunt(l,k,lp,-m,m-mp,mp)) if True else 0
import functools
@functools.lru_cache(None)
def c(k,m,mp):
    return float((-1)**m*2*gaunt(2,k,2,-m,m-mp,mp)) if abs(m-mp)<=k else 0.0
Fk={0:0,2:F2,4:F4}
orb=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
n=10
# V[a,b,c,d]=<ab|1/r12|cd>
V=np.zeros((n,)*4)
for a in range(n):
 for b in range(n):
  for cc in range(n):
   for d in range(n):
    ma,sa=orb[a];mb,sb=orb[b];mc,sc=orb[cc];md,sd=orb[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    t=0
    for k in (2,4):
     t+=Fk[k]/ (1.0)*c(k,ma,mc)*c(k,md,mb)*0+0
    V[a,b,cc,d]=0
# simpler: <ab|cd> = sum_k F^k c^k(ma,mc) c^k(md,mb)
for a in range(n):
 for b in range(n):
  for cc in range(n):
   for d in range(n):
    ma,sa=orb[a];mb,sb=orb[b];mc,sc=orb[cc];md,sd=orb[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    V[a,b,cc,d]=sum(Fk[k]*c(k,ma,mc)*c(k,md,mb) for k in (2,4))
# cubic: Dq term in real basis: use H = Dq*(operator) in |m>: <4|... 
def hcf(Dq):
    h=np.zeros((10,10))
    # d orbitals cubic: 
    for s in (0.5,-0.5):
        idx={m:orb.index((m,s)) for m in range(-2,3)}
        for m in range(-2,3): h[idx[m],idx[m]]+=-4*Dq*0 
        # e: 6Dq, t2:-4Dq ; matrix in |m>: diag 4Dq at m=+-2 , -6Dq at m=0; coupling 5Dq between 2,-2
        for m,v in ((2,.6*10*Dq*0),):pass
        d={2:Dq,-2:Dq,0:6*Dq,1:-4*Dq,-1:-4*Dq}
        # use general: x2-y2 and z2 are e(+6), xy t2(-4) ; xy=(|2>-|-2>)/i√2, x2-y2=(|2>+|-2>)/√2
        h[idx[2],idx[2]]=1*Dq; h[idx[-2],idx[-2]]=1*Dq
        h[idx[2],idx[-2]]=h[idx[-2],idx[2]]=5*Dq
        h[idx[0],idx[0]]=6*Dq
        h[idx[1],idx[1]]=-4*Dq;h[idx[-1],idx[-1]]=-4*Dq
    return h
# dets
dets=[d for d in itertools.combinations(range(n),6)]
def build(sel,Dq):
    ix={d:i for i,d in enumerate(sel)}
    H=np.zeros((len(sel),)*2)
    S2=np.zeros_like(H)
    h=hcf(Dq)
    def apply(det,ops):
        # ops: list of (create/annihilate idx) apply right to left; return sign,newdet
        l=list(det);sign=1
        for typ,i in ops:
            if typ=='a':
                if i not in l: return 0,None
                p=l.index(i);sign*=(-1)**p;l.pop(p)
            else:
                if i in l: return 0,None
                p=sum(1 for x in l if x<i);sign*=(-1)**p;l.insert(p,i)
        return sign,tuple(l)
    for det in sel:
        j=ix[det]
        for a in range(n):
         for b in range(n):
          if h[a,b]!=0:
            s,nd=apply(det,[('a',b),('c',a)])
            if s and nd in ix: H[ix[nd],j]+=s*h[a,b]
        for a in range(n):
         for b in range(n):
          for cc in range(n):
           for d in range(n):
            v=V[a,b,cc,d]
            if v==0: continue
            # 1/2 sum a†b† d c  with <ab|cd> -> a†_a a†_b a_d a_c
            s,nd=apply(det,[('a',cc),('a',d),('c',b),('c',a)])
            if s and nd in ix: H[ix[nd],j]+=0.5*s*v
        # S^2 = S-S+ + Sz^2+Sz
    # S2 via S- S+ ... compute S+ 
    for det in sel:
        j=ix[det]
        sz=sum(orb[i][1] for i in det)
        S2[j,j]+=sz*sz+sz
        # S- S+ : S+ = sum a†_{m up} a_{m dn}
        for m in range(-2,3):
            for m2 in range(-2,3):
                up=orb.index((m,.5));dn=orb.index((m,-.5));up2=orb.index((m2,.5));dn2=orb.index((m2,-.5))
                # S- S+ = sum_{m,m2} a†_{m dn} a_{m up} a†_{m2 up} a_{m2 dn}
                s,nd=apply(det,[('a',dn2),('c',up2),('a',up),('c',dn)])
                if s and nd in ix: S2[ix[nd],j]+=s
    return H,S2
sel0=[d for d in dets if sum(orb[i][1] for i in d)==0]
sel2=[d for d in dets if sum(orb[i][1] for i in d)==2]
def gap(Dq):
    H,S2=build(sel0,Dq)
    w,_=np.linalg.eigh(H+1e6*S2)
    # S=0 lowest: energy with S2~0
    H5,_=build(sel2,Dq)
    e5=np.linalg.eigvalsh(H5)[0]
    H0,S=build(sel0,Dq)
    ww,vv=np.linalg.eigh(H0+1e6*S)
    return ww[0]-e5
for D in (1000,1500,2000):print(D,gap(D))
print(brentq(gap,800,3000))
