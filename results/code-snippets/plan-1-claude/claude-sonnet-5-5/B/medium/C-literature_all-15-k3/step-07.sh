mkdir -p /dev/shm/w && cd /dev/shm/w && cat > d7.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt, pi, N
ms=[2,1,0,-1,-2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float(N((-1)**m1*gaunt(2,k,2,-m1,q,m2)*sqrt(4*pi/(2*k+1))))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for s in (0,1) for m in ms]
idx={x:i for i,x in enumerate(so)}
def build(A,B,Cc,Dq):
    F4=Cc/35; F2=B+5*F4
    Fk={0:A+49*F4,2:49*F2,4:441*F4}
    h=np.zeros((10,10))
    V={2:1,1:-4,0:6,-1:-4,-2:1}
    for s in (0,1):
        for m in ms: h[idx[(m,s)],idx[(m,s)]]=V[m]*Dq
        h[idx[(2,s)],idx[(-2,s)]]=5*Dq; h[idx[(-2,s)],idx[(2,s)]]=5*Dq
    g=np.zeros((10,10,10,10))
    for (a,sa) in so:
      for (b,sb) in so:
        for (c,sc) in so:
          for (d,sd) in so:
            if sa!=sc or sb!=sd or a+b!=c+d: continue
            v=sum(C[(k,a,c)]*C[(k,d,b)]*Fk[k] for k in (0,2,4))
            g[idx[(a,sa)],idx[(b,sb)],idx[(c,sc)],idx[(d,sd)]]=v
    return h,g
def dets(Ms2):
    return [c for c in itertools.combinations(range(10),7) if (2*sum(1 for i in c if i>=5)-7)==Ms2]
def ham(h,g,basis):
    n=len(basis); pos={d:i for i,d in enumerate(basis)}
    H=np.zeros((n,n))
    def ap(det,ops):
        occ=list(det);sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in occ: return 0,None
                p=occ.index(o); sign*=(-1)**p; occ.pop(p)
            else:
                if o in occ: return 0,None
                p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
        return sign,tuple(occ)
    nz=list(zip(*np.nonzero(g)))
    hz=list(zip(*np.nonzero(h)))
    for j,d in enumerate(basis):
        for p,q in hz:
            s,nd=ap(d,[('c',p),('a',q)])
            if s: H[pos[nd],j]+=s*h[p,q]
        for a,b,c,e in nz:
            s,nd=ap(d,[('c',a),('c',b),('a',e),('a',c)])
            if s: H[pos[nd],j]+=0.5*s*g[a,b,c,e]
    return H
b32=dets(3);b12=dets(1)
def levels(A,B,Cc,Dq):
    h,g=build(A,B,Cc,Dq)
    return np.linalg.eigvalsh(ham(h,g,b32)),np.linalg.eigvalsh(ham(h,g,b12))
if __name__=="__main__":
    import time;t=time.time()
    e4,e2=levels(0,900,3900,900)
    print(time.time()-t)
    print(np.round(e4-e4[0],0)); print(np.round(e2-e4[0],0))
E
python3 d7.py