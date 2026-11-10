cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
l=2; ms=list(range(-2,3))
def Cmat(k,q):
    M=np.zeros((5,5)); red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    for ia,ma in enumerate(ms):
        for ib,mb in enumerate(ms):
            if -ma+q+mb!=0: continue
            M[ia,ib]=(-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mb))*red
    return M
def coulomb(Fk):
    V=np.zeros((10,10,10,10))
    for k,F in Fk.items():
        for q in range(-k,k+1):
            A=Cmat(k,q); Bm=Cmat(k,-q)*(-1)**q
            for s1 in range(2):
                for s2 in range(2):
                    for i,kk,j,ll in itertools.product(range(5),repeat=4):
                        v=A[i,kk]*Bm[j,ll]
                        if abs(v)>1e-14: V[s1*5+i,s2*5+j,s1*5+kk,s2*5+ll]+=F*v
    return V
r2=np.sqrt(2)
vecs={'dz2':np.array([0,0,1,0,0],complex),'dx2y2':np.array([1,0,0,0,1],complex)/r2,
 'dxy':np.array([1,0,0,0,-1],complex)/(1j*r2),'dxz':np.array([0,1,0,-1,0],complex)/r2,
 'dyz':np.array([0,1j,0,1j,0],complex)/r2}
U=np.array([vecs[k] for k in vecs]).T; assert np.allclose(U.conj().T@U,np.eye(5))
N=10
def cdag(i):
    M=np.zeros((2**N,2**N))
    for st in range(2**N):
        if not (st>>i)&1: M[st|(1<<i),st]=(-1)**bin(st&((1<<i)-1)).count('1')
    return M
Cc=[cdag(i) for i in range(N)]; Ca=[c.T for c in Cc]
idx=[(1<<i)|(1<<j) for i,j in itertools.combinations(range(5),2)]
def triplets(Dq,F2,F4):
    en={'dz2':6*Dq,'dx2y2':6*Dq,'dxy':-4*Dq,'dxz':-4*Dq,'dyz':-4*Dq}
    h5=sum(en[k]*np.outer(vecs[k],vecs[k].conj()) for k in vecs)
    h=np.zeros((10,10),complex)
    for s in range(2): h[s*5:s*5+5,s*5:s*5+5]=h5
    V=coulomb({2:F2,4:F4})
    # restricted operators: build only in Ms=1 sector to save time: use full Fock but only need matrix elements between idx states
    S=idx
    def op_mat(ops):
        return ops
    H=np.zeros((len(S),len(S)),complex)
    # one-body
    for a in range(N):
        for b in range(N):
            if abs(h[a,b])>1e-14:
                H+= h[a,b]*(Ca[a]@Cc[b])[np.ix_(S,S)]
    for a,b,c,d in itertools.product(range(N),repeat=4):
        v=V[a,b,c,d]
        if abs(v)>1e-14:
            H+=0.5*v*(Ca[a]@Ca[b]@Cc[d]@Cc[c])[np.ix_(S,S)]
    return np.sort(np.linalg.eigvalsh((H+H.conj().T)/2).real)
# check independence of F4 at fixed B=1 (B=(9F2-5F4)/441)
for F4 in [0.0,0.5]:
    F2=(441+5*F4)/9
    print('F4',F4,np.round(triplets(0.7,F2,F4),5))
EOF