
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
# complex d orbitals m=-2..2, spin; Coulomb via Slater integrals F0,F2,F4
def ck(k,l,m1,l2,m2):
    return float(gaunt(l,k,l,-m1,m1-m2,m2)) if False else None
from sympy import Rational
from sympy.physics.wigner import wigner_3j
import math
def c(k,m1,m2):  # <2m1|C^k|2m2>
    return (-1)**m1*5*float(wigner_3j(2,k,2,0,0,0))*float(wigner_3j(2,k,2,-m1,m1-m2,m2))
ms=range(-2,3)
def V(F):
    # <ab|g|cd> = sum_k F_k * c^k(a,c) c^k(b,d) delta
    U={}
    for a,b,cc,d in itertools.product(ms,repeat=4):
        if a+b!=cc+d: continue
        s=0
        for k,Fk in zip((0,2,4),F):
            q=a-cc
            s+=Fk*(-1)**q*c(k,a,cc)*c(k,d,b)   # c^k(a,c)*c^k(d,b)
        U[(a,b,cc,d)]=s
    return U
# orbitals idx (m,spin)
orbs=[(m,s) for m in ms for s in (1,-1)]
# real cubic field: matrix in m basis: Dq*... V = 21Dq/... use operator: dxy..; build via diag in real basis
# real d: z2 (m0), xz,yz,xy,x2-y2. e: z2, x2-y2 ; t2: others
def U_():
    import numpy as np
    s=1/np.sqrt(2)
    # columns: real orbitals in m basis (-2..2)
    R={}
    v=lambda d:np.array([d.get(m,0) for m in ms],complex)
    z2=v({0:1}); x2=v({2:s,-2:s}); xy=v({2:-1j*s*-1,-2:1j*s*-1})
    xy=v({2:-1j*s,-2:1j*s}); xz=v({1:s,-1:-s}); yz=v({1:1j*s,-1:1j*s})
    return z2,x2,xy,xz,yz
z2,x2,xy,xz,yz=U_()
def Hcf(Dq):
    H=np.zeros((5,5),complex)
    for e in (z2,x2): H+=6*Dq*np.outer(e,e.conj())
    for t in (xy,xz,yz): H+=-4*Dq*np.outer(t,t.conj())
    return H
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
n=len(dets);print(n)
def build(Dq,B,C):
    # F2,F4 from B,C: C=35F4/441 ->F4=441C/35; B=F2/49-5F4/441
    F4=441*C/35; F2=49*(B+5*F4/441)
    F=(0,F2,F4)
    Un=V(F)
    h=Hcf(Dq)
    H=np.zeros((n,n),complex)
    for d in dets:
        i=idx[d]
        # one-body
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                el=h[orbs[q][0]+2,orbs[p][0]+2]
                if el==0: continue
                if q!=p and q in d: continue
                nd=list(d);nd[nd.index(p)]=q
                sign=1
                # sign: sort
                lst=nd;perm=sorted(range(5),key=lambda k:lst[k])
                sg=np.linalg.det(np.eye(5)[perm]) if False else 1
                srt=sorted(lst)
                # parity of permutation
                inv=sum(1 for a in range(5) for b in range(a+1,5) if lst[a]>lst[b])
                sg=(-1)**inv
                H[idx[tuple(srt)],i]+=el*sg
        # two-body 1/2 sum <pq|rs> a+p a+q a_s a_r ; build via ops
    return H
E
echo