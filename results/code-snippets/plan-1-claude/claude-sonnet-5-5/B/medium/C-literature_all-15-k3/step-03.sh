mkdir -p /w && cd /w && cat > d7.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt, pi, N
ms=[2,1,0,-1,-2]
def ck(k,m1,m2):
    # sqrt(4pi/(2k+1)) * int Y*_{2m1} Y_{k,m1-m2} Y_{2m2}
    q=m1-m2
    if abs(q)>k: return 0.0
    # int Y*_{l m1} Y_kq Y_{l m2} = (-1)^m1 gaunt(2,k,2,-m1,q,m2)
    return float(N((-1)**m1*gaunt(2,k,2,-m1,q,m2)*sqrt(4*pi/(2*k+1))))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for s in (0,1) for m in ms]  # spin-orbital index
idx={x:i for i,x in enumerate(so)}
def build(A,B,Cc,Dq):
    F4=Cc/35; F2=B+5*F4
    Fk={0:A+49*F4,2:49*F2,4:441*F4}
    # F0 irrelevant constant (use A=0 -> F0=49F4 ; fine)
    h=np.zeros((10,10))
    V={2:1,1:-4,0:6,-1:-4,-2:1}
    for s in (0,1):
        for m in ms: h[idx[(m,s)],idx[(m,s)]]=V[m]*Dq
        h[idx[(2,s)],idx[(-2,s)]]=5*Dq; h[idx[(-2,s)],idx[(2,s)]]=5*Dq
    # two-electron <ab|cd> physics notation: a(1)b(2) c(1)d(2)
    g=np.zeros((10,10,10,10))
    for (a,sa) in so:
      for (b,sb) in so:
        for (c,sc) in so:
          for (d,sd) in so:
            if sa!=sc or sb!=sd or a+b!=c+d: continue
            v=0
            for k in (0,2,4):
                v+=C[(k,a,c)]*C[(k,d,b)]*Fk[k]
            g[idx[(a,sa)],idx[(b,sb)],idx[(c,sc)],idx[(d,sd)]]=v
    return h,g
def dets(Ms2):
    out=[]
    for c in itertools.combinations(range(10),3 if False else 7):
        n_up=sum(1 for i in c if i>=5); n_dn=7-n_up
        if n_up-n_dn==Ms2: out.append(c)
    return out
def ham(h,g,basis):
    n=len(basis); pos={d:i for i,d in enumerate(basis)}
    H=np.zeros((n,n))
    def apply_ops(det,ops):
        # ops list of (type,orb) applied right to left; returns sign,newdet
        occ=list(det);sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in occ: return 0,None
                p=occ.index(o); sign*=(-1)**p; occ.pop(p)
            else:
                if o in occ: return 0,None
                p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
        return sign,tuple(occ)
    for j,d in enumerate(basis):
        for p in range(10):
            for q in range(10):
                if h[p,q]!=0:
                    s,nd=apply_ops(d,[('c',p),('a',q)])
                    if s: H[pos[nd],j]+=s*h[p,q]
        for a in range(10):
         for b in range(10):
          for c in range(10):
           for e in range(10):
            v=g[a,b,c,e]
            if v==0: continue
            # 1/2 sum <ab|ce> a†a b†b e c  -> a†_a a†_b a_e a_c
            s,nd=apply_ops(d,[('c',a),('c',b),('a',e),('a',c)])
            if s and nd in pos: H[pos[nd],j]+=0.5*s*v
    return H
b32=dets(3);b12=dets(1)
import pickle
def levels(A,B,Cc,Dq):
    h,g=build(A,B,Cc,Dq)
    e4=np.linalg.eigvalsh(ham(h,g,b32))
    e2=np.linalg.eigvalsh(ham(h,g,b12))
    return e4,e2
if __name__=="__main__":
    e4,e2=levels(0,900,3900,900)
    print(np.round(e4-e4[0],0)); print(np.round(e2-e4[0],0))
E
python3 d7.py