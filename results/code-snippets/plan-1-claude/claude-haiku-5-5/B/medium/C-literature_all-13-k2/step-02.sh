mkdir -p /w && cat > /w/ls.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.sparse import csr_matrix, kron, identity
from scipy.optimize import least_squares
from math import factorial

# angular grid
xg, wg = np.polynomial.legendre.leggauss(30)
th = np.arccos(xg); ph = np.linspace(0,2*np.pi,64,endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(wg, np.full(64, 2*np.pi/64))
ms = [-2,-1,0,1,2]
def Y(l,m,t,p): return sph_harm(m, l, p, t)   # scipy: sph_harm(m,l,azimuth,polar)
def Ck(k,q,t,p): return np.sqrt(4*np.pi/(2*k+1))*Y(k,q,t,p)
def mat(k,q):  # <a|C^k_q|c> matrix over m
    M = np.zeros((5,5),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            M[i,j] = np.sum(W*np.conj(Y(2,a,TH,PH))*Ck(k,q,TH,PH)*Y(2,c,TH,PH))
    return M
ak = {}
for k in (0,2,4):
    Cm = {q: mat(k,q) for q in range(-k,k+1)}
    A = np.zeros((5,5,5,5),complex)
    for a in range(5):
        for c in range(5):
            for b in range(5):
                for d in range(5):
                    A[a,b,c,d] = sum((-1)**q * Cm[-q][a,c]*Cm[q][b,d] for q in range(-k,k+1))
    ak[k]=A

# one-electron cubic field projector in m basis (z = C4 axis)
Peg = np.zeros((5,5),complex)
Peg[2,2]=1
v = np.zeros(5,complex); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2)  # |2>+|-2>
Peg += np.outer(v,v.conj())
Pt2 = np.eye(5)-Peg
# spin-orbital index: 2*orb + s  (s=0 up, 1 down)
nso=10
# Jordan-Wigner annihilators
I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.])); a_=csr_matrix(np.array([[0,1.],[0,0]]))
def ann(i):
    ops=[Z]*i+[a_]+[I2]*(nso-i-1)
    out=ops[0]
    for o in ops[1:]: out=kron(out,o,format='csr')
    return out
c=[ann(i) for i in range(nso)]
cd=[x.T.conj().tocsr() for x in c]
def so(orb,s): return 2*orb+s

def build(Dq,B,C):
    F4=441*C/35.; F2=(441*B+5*F4)/9.
    F={0:0.0,2:F2,4:F4}
    # one-electron
    h=np.zeros((nso,nso),complex)
    for o1 in range(5):
        for o2 in range(5):
            val=6*Dq*Peg[o1,o2]-4*Dq*Pt2[o1,o2]
            for s in (0,1): h[so(o1,s),so(o2,s)]+=val
    H=csr_matrix((1024,1024),dtype=complex)
    for i in range(nso):
        for j in range(nso):
            if abs(h[i,j])>1e-12: H=H+h[i,j]*(cd[i]@c[j])
    # two-electron: 1/2 sum V_{ab,cd} c+_a c+_b c_d c_c, V_{ab,cd}=sum_k F^k a_k(a,c;b,d)
    for o in itertools.product(range(5),repeat=4):
        a_o,b_o,c_o,d_o=o
        Vv=sum(F[k]*ak[k][a_o,b_o,c_o,d_o] for k in (2,4))  # F0 irrelevant (constant in sector)
        if abs(Vv)<1e-12: continue
        for s1 in (0,1):
            for s2 in (0,1):
                i=so(a_o,s1); j=so(b_o,s2); k_=so(c_o,s1); l=so(d_o,s2)
                H=H+0.5*Vv*(cd[i]@cd[j]@c[l]@c[k_])
    return H
# number and Sz for sector selection
def states_sector(nup,ndn):
    out=[]
    for ups in itertools.combinations(range(5),nup):
        for dns in itertools.combinations(range(5),ndn):
            occ=[so(o,0) for o in ups]+[so(o,1) for o in dns]
            idx=sum(1<<(nso-1-i) for i in occ)  # JW basis: site0 most significant
            out.append(idx)
    return out
EOF
cd /w && python3 -c "
import ls,numpy as np
H=ls.build(1000,1000,4000)
print(H.shape, abs(H-H.getH()).max())
"