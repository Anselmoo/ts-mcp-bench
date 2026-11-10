import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=621.,2851.
F2=(B+C/7)*49; F4=C/35*441
ms=range(-2,3)
def ck(k,m1,m2): # <2m1|c^k|2m2>
    from sympy import sqrt,N
    return float(N((-1)**m1*sqrt(5)*sqrt(5)*gaunt(2,k,2,-m1,m1-m2,m2)*1)) if False else None
from sympy import Ynm
import sympy
def c(k,m1,m2):
    # <l m1|C^k_q|l m2>, q=m1-m2 = (-1)^m1 * 5 * 3j(2 -m1;k q;2 m2)*3j(2 0 k 0 2 0)
    from sympy.physics.wigner import wigner_3j
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,q,m2)*wigner_3j(2,k,2,0,0,0))
Fk={0:0,2:F2/49,4:F4/441}
def V(a,b,cc,d): # <ab|1/r12|cd>, orbitals m; a,c electron1 b,d electron2
    s=0
    for k in (2,4):
        if a-cc==d-b:
            s+=Fk[k]*c(k,a,cc)*c(k,d,b)*(-1)**(a-cc)
    return s
# note F^k (Slater) = Fk dict *? using CS F2cs,F4cs times 49 /441 -> Fk is CS-> but formula uses Slater F^k: 
Fk={2:F2,4:F4}
orbs=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1]==0 for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
U=np.zeros((5,5))
s2=1/np.sqrt(2)
# basis order m=-2..2 ; eg: d0, (d2+d-2)/√2 ; t2: d1,d-1,(d2-d-2)/√2
T=np.zeros((5,5)) # columns = new orbitals in m basis
def ix(m):return m+2
T[ix(0),0]=1;T[ix(2),1]=s2;T[ix(-2),1]=s2
T[ix(1),2]=1;T[ix(-1),3]=1;T[ix(2),4]=s2;T[ix(-2),4]=-s2
def run(Dq):
    e=np.diag([6,6,-4,-4,-4])*Dq
    h1=T@e@T.T
    n=len(dets);H=np.zeros((n,n))
    # build via second quantization numerically
    # one-body
    def apply(det,ops):
        pass
    import collections
    # spin orbital list index i -> (m,s)
    def excite(det,cr,an):
        l=list(det)
        sign=1
        for a in an:
            if a not in l:return None,0
            p=l.index(a);sign*=(-1)**p;l.pop(p)
        for c_ in cr:
            if c_ in l:return None,0
            # insert at sorted position
            l2=sorted(l+[c_]);p=l2.index(c_);sign*=(-1)**p;l=l2
        return tuple(l),sign
    for d in dets:
        i=idx[d]
        for a in range(10):
            for b in range(10):
                if orbs[a][1]!=orbs[b][1]:continue
                h=h1[orbs[a][0]+2,orbs[b][0]+2]
                if abs(h)<1e-12:continue
                nd,s=excite(d,[a],[b])
                if nd: H[idx[nd],i]+=h*s
        for a in range(10):
          for b in range(10):
            for cc in range(10):
              for dd in range(10):
                if orbs[a][1]!=orbs[cc][1] or orbs[b][1]!=orbs[dd][1]:continue
                v=V(orbs[a][0],orbs[b][0],orbs[cc][0],orbs[dd][0])
                if abs(v)<1e-12:continue
                # 1/2 sum v a†a b†b d c  : a†_a a†_b a_d a_c
                nd,s=excite(d,[b,a],[dd,cc]) if False else (None,0)
                # apply a_c then a_d then create b then a
                l=list(d);sign=1;ok=True
                for an in (cc,dd):
                    if an not in l:ok=False;break
                    p=l.index(an);sign*=(-1)**p;l.pop(p)
                if not ok:continue
                for cr in (b,a):
                    if cr in l:ok=False;break
                    l2=sorted(l+[cr]);p=l2.index(cr);sign*=(-1)**p;l=l2
                if ok: H[idx[tuple(l)],i]+=0.5*v*sign
    return H
# spin
def S2():
    n=len(dets);M=np.zeros((n,n))
    # S- S+ + Sz(Sz+1): S+ flips down->up same m
    for d in dets:
        i=idx[d]
        M[i,i]+=0.75*0+ (0.5*0.5+0.5)  # Sz(Sz+1)=0.75
    for d in dets:
        i=idx[d]
        for a in range(10):
          if orbs[a][1]==1 and a in d:
            pass
    return M
