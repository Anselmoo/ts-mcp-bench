
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(5*5)) if abs(m1-m2)<=k else 0.0
# <ab|g|cd> = sum_k F^k c^k(a,c)c^k(b,d) ; c^k(m,m')=(-1)^m sqrt(25)... use gaunt form
from math import sqrt
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*gaunt(2,k,2,-m1,q,m2))
C={ (k,a,b):c(k,a,b) for k in(0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in(0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def build(B,Cc,Dq):
    F4=Cc/35;F2=B+5*F4
    F={0:0,2:F2,4:F4}
    # V[a,b,c,d]=<ab|1/r|cd> spin orbitals
    V=np.zeros((10,10,10,10))
    for a,(ma,sa) in enumerate(so):
     for b,(mb,sb) in enumerate(so):
      for cc,(mc,sc) in enumerate(so):
       for d,(md,sd) in enumerate(so):
        if sa==sc and sb==sd and ma+mb==mc+md:
         V[a,b,cc,d]=sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in(2,4))
    # one-electron
    U=np.zeros((5,5),complex)
    i=lambda m:ms.index(m)
    # real orbitals columns
    vecs=[];en=[]
    e=np.zeros(5,complex);e[i(0)]=1;vecs.append(e);en.append(6*Dq)
    e=np.zeros(5,complex);e[i(2)]=e[i(-2)]=1/sqrt(2);vecs.append(e);en.append(6*Dq)
    e=np.zeros(5,complex);e[i(2)]=1/sqrt(2);e[i(-2)]=-1/sqrt(2);vecs.append(e);en.append(-4*Dq)
    e=np.zeros(5,complex);e[i(1)]=1/sqrt(2);e[i(-1)]=-1/sqrt(2);vecs.append(e);en.append(-4*Dq)
    e=np.zeros(5,complex);e[i(1)]=1/sqrt(2);e[i(-1)]=1/sqrt(2);vecs.append(e);en.append(-4*Dq)
    W=np.array(vecs).T;h5=(W*np.array(en))@W.conj().T
    h=np.zeros((10,10),complex)
    for a,(ma,sa) in enumerate(so):
     for b,(mb,sb) in enumerate(so):
      if sa==sb:h[a,b]=h5[i(ma),i(mb)]
    return V,h
def H(B,Cc,Dq):
    V,h=build(B,Cc,Dq)
    n=len(dets);M=np.zeros((n,n),complex)
    def apply_c(op,d): # op list of (type,orb) applied right to left
        pass
    for j,d in enumerate(dets):
        ds=set(d)
        # one-body
        for p in range(10):
          for q in d:
            if h[p,q]==0: continue
            nd=list(d);
            if p!=q and p in ds: continue
            sgn=1
            l=[x for x in d if x!=q]
            pos_q=d.index(q)
            l2=sorted(l+[p]);pos_p=l2.index(p)
            # sign: remove q: (-1)^pos_q ; insert p at pos_p in list l: (-1)^pos_p
            sgn=(-1)**(pos_q+pos_p)
            M[idx[tuple(l2)],j]+=sgn*h[p,q]
        # two-body 1/2 sum V[a,b,c,d] a+ b+ d c
        for c1 in d:
         for d1 in d:
          if c1==d1: continue
          l=list(d)
          # apply a_d1 then a_c1? operator a+_a a+_b a_d a_c : annihilate c first
          s=1
          p1=l.index(c1);s*=(-1)**p1;l.remove(c1)
          p2=l.index(d1);s*=(-1)**p2;l.remove(d1)
          for a in range(10):
           if a in l: continue
           for b in range(10):
            if b in l or b==a: continue
            v=V[a,b,c1,d1]
            if v==0: continue
            l3=list(l);
            # create b first then a
            pb=sum(1 for x in l3 if x<b);s2=(-1)**pb;l3.append(b);l3.sort()
            pa=sum(1 for x in l3 if x<a);s2*=(-1)**pa;l3.append(a);l3.sort()
            M[idx[tuple(l3)],j]+=0.5*v*s*s2
    return M
def lev(B,Cc,Dq):
    M=H(B,Cc,Dq);w=np.linalg.eigvalsh((M+M.conj().T)/2)
    return w
import sys
w=lev(900,4000,1000);print(np.round(w-w[0],0)[:60:4])
np.save('/tmp/ok',w)
E
python3 /tmp/a.py