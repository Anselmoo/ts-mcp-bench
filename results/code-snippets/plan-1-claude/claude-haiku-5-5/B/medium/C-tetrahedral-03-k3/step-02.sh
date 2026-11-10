mkdir -p /w && cat > /w/d8.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
ms=list(range(-2,3))
def Ck(k):
    M={}
    for q in range(-k,k+1):
        A=np.zeros((5,5))
        for i,m in enumerate(ms):
            for j,mp in enumerate(ms):
                if -m+q+mp==0 and abs(m)<=2 and abs(mp)<=2:
                    A[i,j]=float((-1)**(l-m)*5*wigner_3j(l,k,l,-m,q,mp))
        M[q]=A
    return M
C={k:Ck(k) for k in (0,2,4)}
# angular coefficient tensors f_k[a,c,b,d]
def fk(k):
    f=np.zeros((5,5,5,5))
    for q in range(-k,k+1):
        f+= (-1)**q*np.einsum('ac,bd->acbd',C[k][q],C[k][-q])
    return f
f2,f4=fk(2),fk(4)
f0=fk(0)
# spin orbitals: idx=2*mi+s, s=0 up,1 down
N=10
def eri(F2,F4,F0=0):
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        sa,sb,sc,sd=a%2,b%2,c%2,d%2
        if sa!=sc or sb!=sd: continue
        ma,mb,mc,md=a//2,b//2,c//2,d//2
        V[a,b,c,d]=F0*f0[ma,mc,mb,md]+F2*f2[ma,mc,mb,md]+F4*f4[ma,mc,mb,md]
    return V
# one-electron tetrahedral LF: e (dz2 m=0, dx2-y2 (|2>+|-2>)/sqrt2) at -6Dq; t2 at +4Dq
Pe=np.zeros((5,5)); Pe[2,2]=1
v=np.zeros(5); v[0]=1; v[4]=1; v/=np.sqrt(2); Pe=np.outer(np.eye(5)[2],np.eye(5)[2])+np.outer(v,v)
Pt=np.eye(5)-Pe
def h1(Dq):
    return -6*Dq*Pe+4*Dq*Pt
# determinants: 8 electrons among 10 spin orbitals, Sz=1 sector: n_up=5,n_down=3
dets=[]
for occ in itertools.combinations(range(N),8):
    nup=sum(1 for o in occ if o%2==0)
    if nup==5: dets.append(occ)
idx={d:i for i,d in enumerate(dets)}
def apply_ops(state_occ, ops):
    # ops list of (type,orb) applied right-to-left; state as sorted tuple -> (sign, newtuple) or None
    pass
def H_matrix(Dq,F2,F4):
    V=eri(F2,F4)
    h=np.zeros((N,N))
    H1=h1(Dq)
    for a in range(N):
        for c in range(N):
            if a%2==c%2: h[a,c]=H1[a//2,c//2]
    n=len(dets); H=np.zeros((n,n))
    def annihilate(occ,p):
        if p not in occ: return None
        s=sum(1 for o in occ if o<p)
        return ((-1)**s, tuple(o for o in occ if o!=p))
    def create(occ,p):
        if p in occ: return None
        s=sum(1 for o in occ if o<p)
        return ((-1)**s, tuple(sorted(occ+(p,))))
    for j,occ in enumerate(dets):
        # one-body
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
        # two-body: 1/2 sum V_abcd a+_a a+_b a_d a_c
        for a,b,c,d in itertools.product(range(N),repeat=4):
            if V[a,b,c,d]==0 or a==b or c==d: continue
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
EOF
cd /w && python3 -c "
from d8 import *
import numpy as np
H=H_matrix(0.0,1.0,0.0)
print(len(dets)); print(np.round(np.linalg.eigvalsh(H),4))
"