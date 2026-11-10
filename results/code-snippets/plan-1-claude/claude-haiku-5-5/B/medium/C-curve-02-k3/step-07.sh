cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.linalg import eigh
C=3003/722; F2=49+7*C; F4=12.6*C
ms=[-2,-1,0,1,2]
def Vk(k):
    T=np.zeros((5,5,5,5))
    for a,m1 in enumerate(ms):
     for b,m2 in enumerate(ms):
      for c,m3 in enumerate(ms):
       for d,m4 in enumerate(ms):
        s=0.0
        for q in range(-k,k+1):
            g1=float(gaunt(2,k,2,-m1,-q,m3))
            if g1==0: continue
            g2=float(gaunt(2,k,2,-m2,q,m4))
            s+=(-1)**((m1+q)%2)*g1*(-1)**(m2%2)*g2
        T[a,b,c,d]=s*4*np.pi/(2*k+1)
    return T
V2=Vk(2);V4=Vk(4)
# check: free-ion F0 part not needed; quick sanity: sum rule
N=10
def so(i): return i//2,i%2
def create(i,st):
    if i in st: return None
    p=sum(1 for x in st if x<i); return ((-1)**p,tuple(sorted(st+(i,))))
def annih(i,st):
    if i not in st: return None
    p=st.index(i); return ((-1)**p,tuple(x for x in st if x!=i))
dets=list(itertools.combinations(range(N),3)); ix={d:n for n,d in enumerate(dets)}; D=len(dets)
def build(F2,F4):
    Vso={}
    for i,j,k,l in itertools.product(range(N),repeat=4):
        mi,si=so(i);mj,sj=so(j);mk,sk=so(k);ml,sl=so(l)
        if si!=sk or sj!=sl: continue
        v=F2*V2[mi,mj,mk,ml]+F4*V4[mi,mj,mk,ml]
        if abs(v)>1e-12: Vso[(i,j,k,l)]=v
    H=np.zeros((D,D))
    for n,st in enumerate(dets):
        for (i,j,k,l),v in Vso.items():
            r=annih(k,st)
            if r is None: continue
            s1,st1=r; r=annih(l,st1)
            if r is None: continue
            s2,st2=r; r=create(j,st2)
            if r is None: continue
            s3,st3=r; r=create(i,st3)
            if r is None: continue
            s4,st4=r
            H[ix[st4],n]+=0.5*v*s1*s2*s3*s4
    return H
H=build(F2,F4)
# quartet M_S=3/2 determinants: all spin up
qd=[n for n,d in enumerate(dets) if all(so(x)[1]==0 for x in d)]
print("quartet Coulomb eigen (B=1):", np.round(np.linalg.eigvalsh(H[np.ix_(qd,qd)]),4))
EOF