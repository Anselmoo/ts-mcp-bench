mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2
# spin-orbitals: index = 2*(m+2) + (0 for up, 1 for down)
def idx(m,s): return 2*(m+2)+(0 if s>0 else 1)
SO=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=10
def ang(k,m1,q,m3):
    # <l m1|C^k_q|l m3>
    if m1-m3!=q: return 0.0
    w1=float(wigner_3j(l,k,l,-m1,q,m3))
    w0=float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(m1%2)*(2*l+1)*w1*w0
def Vang(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+=(-1)**(q%2)*ang(k,m1,q,m3)*ang(k,m2,-q,m4)
    return s
# one-body Dq matrix (per spin-orbital), eg projector
def onebody():
    h=np.zeros((N,N))
    # eg subspace in orbital basis of m
    Peg=np.zeros((5,5))
    # m index: m+2
    Peg[2,2]=1.0
    v=np.zeros(5); v[0]=1/sqrt(2); v[4]=1/sqrt(2)
    Peg+=np.outer(v,v)
    Pt=np.eye(5)-Peg
    # return Hcf per unit Dq: 6*Peg - 4*Pt
    H=6*Peg-4*Pt
    for m1 in range(5):
        for m2 in range(5):
            for s in (1,-1):
                h[idx(m1-2,s),idx(m2-2,s)]=H[m1,m2]
    return h
def V_tensor(k):
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        ma,sa=SO[a]; mb,sb=SO[b]; mc,sc=SO[c]; md,sd=SO[d]
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=Vang(k,ma,mb,mc,md)
    return V
# determinant basis
def dets(n):
    out=[]
    for occ in itertools.combinations(range(N),n):
        out.append(occ)
    return out
def apply_op(ops,occ):
    # ops: list of (type,index) applied right-to-left: ops[-1] acts first
    st=list(occ); sign=1
    for typ,i in reversed(ops):
        if typ=='c':  # annihilate
            if i not in st: return None,0
            p=st.index(i); sign*= (-1)**p; st.pop(p)
        else:  # create
            if i in st: return None,0
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
def build(n,hone,Vt):
    D=dets(n); ind={d:i for i,d in enumerate(D)}
    H=np.zeros((len(D),len(D)))
    for j,occ in enumerate(D):
        # one-body
        for a in range(N):
            for b in range(N):
                if abs(hone[a,b])<1e-14: continue
                st,sg=apply_op([('c',a),('a',b)],occ) if False else (None,0)
                st,sg=apply_op([('c',a),('d',b)],occ)
                if st is None: continue
                H[ind[st],j]+=sg*hone[a,b]
        # two-body 1/2 sum V_abcd a+_a a+_b a_d a_c
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=Vt[a,b,c,d]
            if abs(v)<1e-14: continue
            st,sg=apply_op([('c',a),('c',b),('d',d),('d',c)],occ)
            if st is None: continue
            H[ind[st],j]+=0.5*sg*v
    return D,H
EOF
echo ok