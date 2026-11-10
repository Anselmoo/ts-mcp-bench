import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=821.;C=3657.
F4=C/35;F2=B+5*F4
F={0:0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2 m1|c^k|2 m2>
    return float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1*np.sqrt(5)*np.sqrt(5)/np.sqrt(2*k+1)*np.sqrt(2*k+1)/1) if False else None
from sympy import sqrt as ssqrt
def c(k,m1,m2):
    # <m1|c^k_{m1-m2}|m2> = (-1)^m1 * 5 * 3j(2 -m1; k q; 2 m2)... use gaunt: int Y2m1* Y_kq Y2m2 *sqrt(4pi/(2k+1))
    q=m1-m2
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2)*ssqrt(4*3.141592653589793/(2*k+1))) if abs(q)<=k else 0.
C_={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
def V(a,b,cc,d): # <a b|g|c d>, a,c electron1 ; b,d electron2
    s=0
    for k in (2,4):
        if a-cc==d-b: s+=C_[(k,a,cc)]*C_[(k,d,b)]*F[k]
    return s
orbs=[(m,s) for m in ms for s in (0,1)]
n=10
dets=list(itertools.combinations(range(n),4))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# one-body
h=np.zeros((n,n))
for i,(m,s) in enumerate(orbs):
    for j,(m2,s2) in enumerate(orbs):
        if s!=s2: continue
        val=0
        if m==m2: val={0:6,1:-4,-1:-4,2:1,-2:1}[m]
        if (m,m2) in((2,-2),(-2,2)): val=5
        h[i,j]=val
def apply(ops,det):
    # ops list of (idx,create?) applied right to left
    d=list(det);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in d: return None,0
            pos=sum(1 for x in d if x<o); sign*=(-1)**pos; d.insert(pos,o)
        else:
            if o not in d: return None,0
            pos=d.index(o); sign*=(-1)**pos; d.pop(pos)
    return tuple(d),sign
def run(Dq):
    H=np.zeros((N,N))
    for I,det in enumerate(dets):
        for i in range(n):
            for j in range(n):
                if h[i,j]!=0:
                    d,s=apply([(i,1),(j,0)],det)
                    if d: H[idx[d],I]+=s*h[i,j]*Dq
    # two body 1/2 sum <pq|rs> a+p a+q a_s a_r
    for p in range(n):
     for q in range(n):
      if p==q: continue
      for r in range(n):
       for s_ in range(n):
        if r==s_: continue
        (mp,sp),(mq,sq),(mr,sr),(ms_,ss)=orbs[p],orbs[q],orbs[r],orbs[s_]
        if sp!=sr or sq!=ss: continue
        v=V(mp,mq,mr,ms_)
        if v==0: continue
        for I,det in enumerate(dets):
            d,sg=apply([(p,1),(q,1),(s_,0),(r,0)],det)
            if d: H[idx[d],I]+=0.5*sg*v
    e=np.linalg.eigvalsh((H+H.T)/2)
    return e
import sys
for x in (0.9,2.15,3.35):
    e=run(x*B); e=e-e[0]
    lv=[];
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    print(x,[(round(v/B,3),k) for v,k in lv[:8]])
