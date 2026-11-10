cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from sympy import N
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float(N((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp)))
def build(B,C,Dq):
    F2=B+C/7; F4=C/35
    F={0:0,2:F2,4:F4}
    ms=[-2,-1,0,1,2]
    # orbital basis: spin orbitals index (m,s)
    so=[(m,s) for m in ms for s in (0,1)]
    n=10
    ck={k:{(a,b):c(k,a,b) for a in ms for b in ms} for k in (2,4)}
    def g(a,b,cc,d):  # <ab|g|cd>
        if a[1]!=cc[1] or b[1]!=d[1]: return 0
        return sum(F[k]*ck[k][(a[0],cc[0])]*ck[k][(d[0],b[0])] for k in (2,4))
    # one-body: octahedral V in m basis (z axis C4): Dq*(...) : 
    # t2/eg: eg = z2 (m=0), (m=2 + m=-2)/√2 ; t2 others. V=6Dq on eg, -4Dq on t2
    h=np.zeros((5,5))
    P=np.zeros((5,5))
    def vec(d):
        v=np.zeros(5);
        for m,x in d.items(): v[m+2]=x
        return v
    r=2**-.5
    eg=[vec({0:1}),vec({2:r,-2:r})]
    for v in eg: h+=10*Dq*np.outer(v,v)
    # shift so t2 = 0
    H1=np.zeros((n,n))
    for i,a in enumerate(so):
        for j,b in enumerate(so):
            if a[1]==b[1]: H1[i,j]=h[a[0]+2,b[0]+2]
    dets=list(itertools.combinations(range(n),6))
    idx={d:i for i,d in enumerate(dets)}
    G=np.zeros((n,n,n,n))
    for i in range(n):
     for j in range(n):
      for k in range(n):
       for l in range(n):
        G[i,j,k,l]=g(so[i],so[j],so[k],so[l])
    H=np.zeros((len(dets),)*2)
    def apply_a(op,d):  # annihilate/create sequences
        return None
    # second quantization
    def ann(p,d):
        if p not in d: return None
        s=(-1)**sum(1 for x in d if x<p); return s,tuple(x for x in d if x!=p)
    def cre(p,d):
        if p in d: return None
        s=(-1)**sum(1 for x in d if x<p); return s,tuple(sorted(d+(p,)))
    for di,d in enumerate(dets):
        for p in range(n):
         for q in range(n):
            if H1[p,q]!=0:
                r1=ann(q,d)
                if r1:
                    r2=cre(p,r1[1])
                    if r2: H[idx[r2[1]],di]+=H1[p,q]*r1[0]*r2[0]
        # two-body 1/2 sum <pq|g|rs> a†p a†q a_s a_r
        for r_ in d:
         for s_ in d:
          if r_==s_: continue
          r1=ann(r_,d); r2=ann(s_,r1[1]); sg=r1[0]*r2[0]
          for p in range(n):
           for q in range(n):
            val=G[p,q,r_,s_]
            if abs(val)<1e-12: continue
            r3=cre(q,r2[1])
            if not r3: continue
            r4=cre(p,r3[1])
            if not r4: continue
            H[idx[r4[1]],di]+=0.5*val*sg*r3[0]*r4[0]
    return H
def levels(B,C,Dq):
    H=build(B,C,Dq)
    w=np.linalg.eigvalsh(H)
    # (degeneracies included) get distinct levels
    out=[]
    for x in w:
        if not out or abs(x-out[-1][0])>1e-6: out.append([x,1])
        else: out[-1][1]+=1
    return out
if __name__=="__main__":
    for L in levels(500,2000,2000)[:12]: print(L)
E
python3 /tmp/a.py