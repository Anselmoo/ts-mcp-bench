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
N=10
def so(i): return i//2,i%2
def create(i,st):
    if i in st: return None
    p=sum(1 for x in st if x<i); return ((-1)**p,tuple(sorted(st+(i,))))
def annih(i,st):
    if i not in st: return None
    p=st.index(i); return ((-1)**p,tuple(x for x in st if x!=i))
dets=[d for d in itertools.combinations(range(N),3) if all(so(x)[1]==0 for x in d)]
ix={d:n for n,d in enumerate(dets)}; D=len(dets)
Vso={}
for i,j,k,l in itertools.product(range(N),repeat=4):
    mi,si=so(i);mj,sj=so(j);mk,sk=so(k);ml,sl=so(l)
    if si!=sk or sj!=sl: continue
    v=F2*V2[mi,mj,mk,ml]+F4*V4[mi,mj,mk,ml]
    if abs(v)>1e-12: Vso[(i,j,k,l)]=v
def opH(hfun):
    H=np.zeros((D,D))
    for n,st in enumerate(dets):
        for (i,j,k,l),v in Vso.items():
            pass
    return H
Hee=np.zeros((D,D))
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
        if st4 in ix: Hee[ix[st4],n]+=0.5*v*s1*s2*s3*s4
Peg=np.zeros((5,5)); Peg[2,2]=1
v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2); Peg+=np.outer(v,v)
h=6*Peg-4*(np.eye(5)-Peg)
Hcf=np.zeros((D,D))
for n,st in enumerate(dets):
    for i in range(N):
        for j in range(N):
            if so(i)[1]!=0 or so(j)[1]!=0: continue
            if abs(h[so(i)[0],so(j)[0]])<1e-14: continue
            r=annih(j,st)
            if r is None: continue
            s1,st1=r; r=create(i,st1)
            if r is None: continue
            s2,st2=r
            Hcf[ix[st2],n]+=h[so(i)[0],so(j)[0]]*s1*s2
print("Hcf eig", np.round(eigh(Hcf)[0],4))
print("Hee eig", np.round(eigh(Hee)[0],4))
for Dq in [0,1,2.2,3.5]:
    print(Dq, np.round(eigh(Hee+Dq*Hcf)[0],4))
EOF