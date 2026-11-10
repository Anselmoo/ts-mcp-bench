import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
def ck(k,m,mp):
    return float((-1)**m*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V1(m,mp):
    if m==mp: return {0:6,1:-4,-1:-4,2:1,-2:1}[m]
    if abs(m-mp)==4: return 5
    return 0
def g(a,b,c,d,F):  # <ab|1/r|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(ck(k,ma,mc)*ck(k,md,mb)*F[k] for k in (2,4))
def build(Dq,B,C):
    F={2:49*B+7*C,4:441*C/35}
    n=len(dets);H=np.zeros((n,n))
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            # use second quantization generic
            pass
    # second quantization
    def apply(ops,state):
        # ops list of (idx,dag) applied right to left; state tuple sorted
        st=list(state);sign=1
        for o,dag in reversed(ops):
            if dag:
                if o in st: return None,0
                pos=sum(1 for x in st if x<o); sign*=(-1)**pos; st.insert(pos,o)
            else:
                if o not in st: return None,0
                pos=st.index(o); sign*=(-1)**pos; st.pop(pos)
        return tuple(st),sign
    for j,e in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V1(so[p][0],so[q][0])*Dq
                if v==0: continue
                s,sg=apply([(p,1),(q,0)],e)
                if s: H[idx[s],j]+=sg*v
        for a in range(10):
          for b in range(10):
            for c in e:
              for d in e:
                v=g(a,b,c,d,F)
                if v==0: continue
                s,sg=apply([(a,1),(b,1),(d,0),(c,0)],e)
                if s: H[idx[s],j]+=0.5*sg*v
    return H
cache={}
def levels(Dq,B,C):
    w=np.linalg.eigvalsh(build(Dq,B,C)); w=w-w[0]
    # group degeneracies
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((round(w[i],1),j-i)); i=j
    return out
import sys
print(levels(1449,599.3,3000)[:8])
