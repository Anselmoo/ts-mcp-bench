
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
def U(a,b,c,d,F):  # <ab|1/r|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (0,2,4))
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    F={0:0,2:49*B+7*C,4:12.6*C}
    V=np.zeros((10,10))
    for i,(m,s) in enumerate(so):
        V[i,i]=Dq*{0:6,1:-4,-1:-4,2:1,-2:1}[m]
    for i,(m,s) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s==s2 and abs(m-m2)==4: V[i,j]=5*Dq
    n=len(dets);M=np.zeros((n,n))
    def apply(ops,det):
        # ops: list of (create?,orb) applied right to left
        d=list(det);sign=1
        for cr,o in reversed(ops):
            if cr:
                if o in d: return None,0
                p=sum(1 for x in d if x<o); sign*=(-1)**p; d.append(o); d.sort()
            else:
                if o not in d: return None,0
                p=d.index(o); sign*=(-1)**p; d.remove(o)
        return tuple(d),sign
    for J,det in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if V[p,q]!=0:
                    r,s=apply([(1,p),(0,q)],det)
                    if r: M[idx[r],J]+=V[p,q]*s
        for p in range(10):
         for q in range(10):
          for r_ in det:
           for s_ in det:
            u=U(p,q,r_,s_,F)
            if u==0: continue
            r,s=apply([(1,p),(1,q),(0,s_),(0,r_)],det)
            if r: M[idx[r],J]+=0.5*u*s
    return np.linalg.eigvalsh(M)
Dq,B=1917,824
def lev(C):
    e=H(Dq,B,C); e=e-e[0]; return np.unique(np.round(e,2))
print(lev(4*B)[:8])
f=lambda C: lev(C)[1]-17050
Cs=brentq(f,2000,5000); print(Cs, Cs/B, lev(Cs)[:8])
EOF
python3 /tmp/d3.py
