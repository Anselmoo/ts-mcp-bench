cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
n=len(orbs)
CK={(k,m,mp):ck(k,m,mp) for k in (2,4) for m in range(-2,3) for mp in range(-2,3)}
def g(a,b,c,d,Fk):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(CK[(k,ma,mc)]*CK[(k,md,mb)]*Fk[k] for k in (2,4))
dets=list(itertools.combinations(range(n),3))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    Fk={2:49*(B+C/7),4:441*C/35}
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(orbs):
        for j,(mp,sp) in enumerate(orbs):
            if s!=sp: continue
            if m==mp: h[i,j]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
            elif abs(m-mp)==4: h[i,j]=5*Dq
    # second quantization brute force
    N=len(dets);H=np.zeros((N,N))
    def apply(ops,det):
        # ops list of (idx,create?) applied right to left
        st=list(det);sign=1
        for o,cr in reversed(ops):
            if cr:
                if o in st: return None,0
                pos=sum(1 for x in st if x<o);sign*=(-1)**pos;st.insert(pos,o)
            else:
                if o not in st: return None,0
                pos=st.index(o);sign*=(-1)**pos;st.pop(pos)
        return tuple(st),sign
    for J,d in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if h[p,q]==0: continue
                r,s=apply([(p,1),(q,0)],d)
                if r: H[idx[r],J]+=s*h[p,q]
        for p in range(n):
         for q in range(n):
          for r_ in range(n):
           for s_ in range(n):
            v=g(p,q,r_,s_,Fk)
            if v==0: continue
            r,s=apply([(p,1),(q,1),(s_,0),(r_,0)],d)
            if r: H[idx[r],J]+=0.5*s*v
    return H
# S^2
def S2():
    N=len(dets);M=np.zeros((N,N))
    for J,d in enumerate(dets):
        ms=sum(orbs[i][1] for i in d)/2
        M[J,J]+=ms*ms
        # S+S- = S^2 - Sz^2 + Sz  -> S^2 = S-S+ + Sz^2 + Sz
        M[J,J]+=ms
        # S-S+ : sum over a,b  a_{m-}^+ a_{m+} a_{m'+}^+ a_{m'-}
        pass
    return M
def levels(Dq,B,C):
    H=build(Dq,B,C);w,v=np.linalg.eigh(H)
    # spin via Ms: use only Ms=1/2 block and Ms=3/2 block
    ms=np.array([sum(orbs[i][1] for i in d) for d in dets])
    return H,ms
def spec(Dq,B,C):
    H,ms=levels(Dq,B,C)
    b32=np.where(ms==3)[0];b12=np.where(ms==1)[0]
    e32=np.linalg.eigvalsh(H[np.ix_(b32,b32)]);e12=np.linalg.eigvalsh(H[np.ix_(b12,b12)])
    e0=e32.min()
    q=np.unique(np.round(e32-e0,3))
    # doublets: levels in e12 not in e32
    allv=np.round(e12-e0,3)
    from collections import Counter
    c12=Counter(allv);c32=Counter(np.round(e32-e0,3))
    d=sorted(k for k in c12 if c12[k]>c32.get(k,0))
    return q,d
EOF
cd /tmp && python3 -c "
from d3 import *
q,d=spec(1417,878,3500);print(q[:5],d[:4])"