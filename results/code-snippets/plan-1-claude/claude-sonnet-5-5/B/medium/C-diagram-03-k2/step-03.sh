mkdir -p /tmp/w && cd /tmp/w && cat > ts.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from sympy import N
l=2; ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*(2*l+1)*N(wigner_3j(l,k,l,0,0,0))*N(wigner_3j(l,k,l,-m,q,mp)))
C={(k,a,b):ck(k,ms[a],ms[b]) for k in (2,4) for a in range(5) for b in range(5)}
orbs=[(a,s) for a in range(5) for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),5)]
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    # ops list of (type,orb) applied right to left; returns (sign,newdet) or None
    s=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in s: return None
            p=s.index(o); sign*=(-1)**p; s.remove(o)
        else:
            if o in s: return None
            p=sum(1 for x in s if x<o); sign*=(-1)**p; s.insert(p,o)
    return sign,tuple(s)
def build(B,Cc,Dq):
    F={2:49*B+7*Cc,4:12.6*Cc}
    n=len(dets); H=np.zeros((n,n))
    # one-body
    h=np.zeros((5,5))
    for i,m in enumerate(ms): h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    # two-body: 1/2 sum <ab|cd> a+_a b+_b d_? ; <ab|g|cd>=sum_k ck(a,c)ck(d,b)F^k, m_a+m_b=m_c+m_d
    V={}
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        if ms[a]+ms[b]!=ms[c]+ms[d]: continue
        v=sum(C[(k,a,c)]*C[(k,d,b)]*F[k] for k in (2,4))
        if abs(v)>1e-12: V[(a,b,c,d)]=v
    for j,det in enumerate(dets):
        for (a,b,c,d),v in V.items():
            for s1 in (0,1):
              for s2 in (0,1):
                A,Bo,Cq,D=2*a+s1,2*b+s2,2*c+s1,2*d+s2
                r=apply_ops(det,[('c',A),('c',Bo),('a',D),('a',Cq)])
                if r: H[idx[r[1]],j]+=0.5*v*r[0]
        for a in range(5):
          for c in range(5):
            if h[a,c]==0: continue
            for s in (0,1):
                r=apply_ops(det,[('c',2*a+s),('a',2*c+s)])
                if r: H[idx[r[1]],j]+=h[a,c]*r[0]
    return H
def Smat():
    n=len(dets); S2=np.zeros((n,n))
    def op(j,ops): return apply_ops(dets[j],ops)
    for j,det in enumerate(dets):
        sz=sum(0.5 if o%2==0 else -0.5 for o in det)
        S2[j,j]+=sz*sz-sz*0  # sz^2 - ... handled below
        S2[j,j]+=sz   # S-S+ = ... S2=Sz^2+Sz+S-S+
        for a in range(5):
            r=op(j,[('c',2*a+1),('a',2*a)])  # S- ... a†_down a_up? up=0
            if r is None: continue
            # S+ S-: apply S- then... compute S+ S-?? use S2=Sz^2 - Sz + S+S-  ; fix below
    return None
E
echo ok