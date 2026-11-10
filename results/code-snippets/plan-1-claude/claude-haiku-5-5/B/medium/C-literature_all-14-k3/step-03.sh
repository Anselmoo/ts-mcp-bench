mkdir -p /tmp/w && cd /tmp/w && cat > ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2; N=10
def idx(m,s): return 2*(m+2)+(0 if s>0 else 1)
SO=[(m,s) for m in range(-2,3) for s in (1,-1)]
def ang(k,m1,q,m3):
    if m1-m3!=q: return 0.0
    w1=float(wigner_3j(l,k,l,-m1,q,m3)); w0=float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(m1%2)*(2*l+1)*w1*w0
def Vang(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+=(-1)**(q%2)*ang(k,m1,q,m3)*ang(k,m2,-q,m4)
    return s
def onebody():
    Peg=np.zeros((5,5)); Peg[2,2]=1.0
    v=np.zeros(5); v[0]=1/sqrt(2); v[4]=1/sqrt(2); Peg+=np.outer(v,v)
    Pt=np.eye(5)-Peg; H=6*Peg-4*Pt
    h=np.zeros((N,N))
    for m1 in range(5):
        for m2 in range(5):
            for s in (1,-1): h[idx(m1-2,s),idx(m2-2,s)]=H[m1,m2]
    return h
def Vtensor(k):
    V=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        ma,sa=SO[a]; mb,sb=SO[b]; mc,sc=SO[c]; md,sd=SO[d]
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=Vang(k,ma,mb,mc,md)
    return V
def apply_op(ops,occ):
    st=list(occ); sign=1
    for typ,i in reversed(ops):
        if typ=='an':
            if i not in st: return None,0
            p=st.index(i); sign*=(-1)**p; st.pop(p)
        else:
            if i in st: return None,0
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
def build(n,hone,Vt):
    D=list(itertools.combinations(range(N),n)); ind={d:i for i,d in enumerate(D)}
    H=np.zeros((len(D),len(D)))
    for j,occ in enumerate(D):
        for a in range(N):
            for b in range(N):
                if abs(hone[a,b])<1e-14: continue
                st,sg=apply_op([('cr',a),('an',b)],occ)
                if st is not None: H[ind[st],j]+=sg*hone[a,b]
        for a,b,c,d in itertools.product(range(N),repeat=4):
            v=Vt[a,b,c,d]
            if abs(v)<1e-14: continue
            st,sg=apply_op([('cr',a),('cr',b),('an',d),('an',c)],occ)
            if st is not None: H[ind[st],j]+=0.5*sg*v
    return D,H
EOF
cat > run.py << 'EOF'
from ts import *
import numpy as np
h=onebody()
# Racah: F2=49B+7C, F4=63C/5 ; V = F2*V2 + F4*V4 (+F0 const dropped)
V2=Vtensor(2); V4=Vtensor(4)
D,Hcf=build(7,h,np.zeros((N,)*4))
_,H2=build(7,np.zeros((N,N)),V2)
_,H4=build(7,np.zeros((N,N)),V4)
np.savez('mats.npz',Hcf=Hcf,H2=H2,H4=H4)
# S^2 matrix
def S2(D):
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build via one-body operators
    n=len(D); ind={d:i for i,d in enumerate(D)}
    Sz=np.zeros((n,n)); Sp=np.zeros((n,n))
    for j,occ in enumerate(D):
        for m in range(-2,3):
            up,dn=idx(m,1),idx(m,-1)
            Sz[j,j]+=0.5*((up in occ)-(dn in occ))
            st,sg=apply_op([('cr',up),('an',dn)],occ)
            if st is not None: Sp[ind[st],j]+=sg
    Sm=Sp.T
    return Sz@Sz+0.5*(Sp@Sm+Sm@Sp)
np.save('S2.npy',S2(D))
print(len(D))
EOF
time python3 run.py