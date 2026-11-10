import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
ms=list(range(-2,3))
def Ck(k):
    M={}
    for q in range(-k,k+1):
        A=np.zeros((5,5))
        for i,m in enumerate(ms):
            for j,mp in enumerate(ms):
                if -m+q+mp==0:
                    A[i,j]=float((-1)**(l-m)*5*wigner_3j(l,k,l,-m,q,mp))
        M[q]=A
    return M
C={k:Ck(k) for k in (0,2,4)}
def fk(k):
    f=np.zeros((5,5,5,5))
    for q in range(-k,k+1):
        f+= (-1)**q*np.einsum('ac,bd->acbd',C[k][q],C[k][-q])
    return f
f0,f2,f4=fk(0),fk(2),fk(4)
N=10
def eri(F2,F4,F0=0):
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        if a%2!=c%2 or b%2!=d%2: continue
        ma,mb,mc,md=a//2,b//2,c//2,d//2
        V[a,b,c,d]=F0*f0[ma,mc,mb,md]+F2*f2[ma,mc,mb,md]+F4*f4[ma,mc,mb,md]
    return V
Pe=np.zeros((5,5))
v=np.zeros(5); v[0]=1; v[4]=1; v/=np.sqrt(2)
Pe=np.outer(np.eye(5)[2],np.eye(5)[2])+np.outer(v,v)
Pt=np.eye(5)-Pe
dets=[]
for occ in itertools.combinations(range(N),8):
    if sum(1 for o in occ if o%2==0)==5: dets.append(occ)
idx={d:i for i,d in enumerate(dets)}
def annihilate(occ,p):
    if p not in occ: return None
    s=sum(1 for o in occ if o<p)
    return ((-1)**s, tuple(o for o in occ if o!=p))
def create(occ,p):
    if p in occ: return None
    s=sum(1 for o in occ if o<p)
    return ((-1)**s, tuple(sorted(occ+(p,))))
def H_matrix(Dq,F2,F4):
    V=eri(F2,F4)
    H1=-6*Dq*Pe+4*Dq*Pt
    h=np.zeros((N,N))
    for a in range(N):
        for c in range(N):
            if a%2==c%2: h[a,c]=H1[a//2,c//2]
    n=len(dets); H=np.zeros((n,n))
    for j,occ in enumerate(dets):
        for a in range(N):
            for c in range(N):
                if h[a,c]==0: continue
                r=annihilate(occ,c)
                if r is None: continue
                s1,o1=r
                r2=create(o1,a)
                if r2 is None: continue
                s2,o2=r2
                if o2 in idx: H[idx[o2],j]+=s1*s2*h[a,c]
        for a,b,c,d in itertools.product(range(N),repeat=4):
            if V[a,b,c,d]==0: continue
            r=annihilate(occ,c)
            if r is None: continue
            s1,o1=r
            r=annihilate(o1,d)
            if r is None: continue
            s2,o2=r
            r=create(o2,b)
            if r is None: continue
            s3,o3=r
            r=create(o3,a)
            if r is None: continue
            s4,o4=r
            if o4 in idx: H[idx[o4],j]+=0.5*V[a,b,c,d]*s1*s2*s3*s4
    return H
