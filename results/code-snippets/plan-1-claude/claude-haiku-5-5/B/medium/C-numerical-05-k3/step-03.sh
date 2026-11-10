mkdir -p /tmp/ld && cat > /tmp/ld/d2.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve, brentq
l=2
ms=list(range(-2,3))
def Ck(k,q):
    M=np.zeros((5,5))
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    for ia,ma in enumerate(ms):
        for ib,mb in enumerate(ms):
            if ma+ (-q) ... if False else None
    return M
def Cmat(k,q):
    M=np.zeros((5,5))
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    for ia,ma in enumerate(ms):
        for ib,mb in enumerate(ms):
            if -ma+q+mb!=0: continue
            M[ia,ib]=(-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mb))*red
    return M
# spin-orbital index: orbital i (0..4) spin s (0 up,1 down): idx = s*5+i
def coulomb_complex(Fk):
    V=np.zeros((10,10,10,10))
    for k,F in Fk.items():
        for q in range(-k,k+1):
            A=Cmat(k,q); Bm=Cmat(k,-q)*(-1)**q
            for s1 in range(2):
                for s2 in range(2):
                    # <a b|V|c d> with a,c spin s1, b,d spin s2
                    for i in range(5):
                        for j in range(5):
                            for kk in range(5):
                                for ll in range(5):
                                    v=A[i,kk]*Bm[j,ll]
                                    if abs(v)>1e-14:
                                        V[s1*5+i,s2*5+j,s1*5+kk,s2*5+ll]+=F*v
    return V
def build(Dq,Fk):
    # real basis unitary
    r2=np.sqrt(2)
    vecs={
     'dz2':np.array([0,0,1,0,0],complex),
     'dx2y2':np.array([1,0,0,0,1],complex)/r2,
     'dxy':np.array([1,0,0,0,-1],complex)/(1j*r2),
     'dxz':np.array([0,1,0,-1,0],complex)/r2,
     'dyz':np.array([0,1j,0,1j,0],complex)/r2}
    energies={'dz2':6*Dq,'dx2y2':6*Dq,'dxy':-4*Dq,'dxz':-4*Dq,'dyz':-4*Dq}
    h5=np.zeros((5,5),complex)
    for k,v in vecs.items(): h5+=energies[k]*np.outer(v,v.conj())
    U=np.array([vecs[k] for k in vecs]).T  # columns orthonormal?
    assert np.allclose(U.conj().T@U,np.eye(5)),"not orthonormal"
    h=np.zeros((10,10),complex)
    for s in range(2): h[s*5:s*5+5,s*5:s*5+5]=h5
    V=coulomb_complex(Fk)
    return h,V
# Fock space ops on 10 modes
N=10
def cdag(i):
    dim=2**N; M=np.zeros((dim,dim))
    for st in range(dim):
        if not (st>>i)&1:
            sign=(-1)**bin(st & ((1<<i)-1)).count('1')
            M[st|(1<<i),st]=sign
    return M
C=[cdag(i) for i in range(N)]
Cd=[c.T for c in C]
def hamiltonian(Dq,Fk):
    h,V=build(Dq,Fk)
    H=np.zeros((2**N,2**N),complex)
    for a in range(N):
        for b in range(N):
            if abs(h[a,b])>1e-14: H+=h[a,b]*C[a]@Cd[b]
    # 1/2 sum V_abcd c+a c+b c_d c_c
    for a,b,c,d in itertools.product(range(N),repeat=4):
        v=V[a,b,c,d]
        if abs(v)>1e-14:
            H+=0.5*v*(C[a]@C[b]@Cd[d]@Cd[c])
    return H
def sector(H):
    # Ms=1 sector: N=2 with both spins up (orbitals 0..4)
    idx=[]
    for i,j in itertools.combinations(range(5),2):
        idx.append((1<<i)|(1<<j))
    # ensure all N=2 Ms=1 states
    Hs=H[np.ix_(idx,idx)]
    return np.linalg.eigvalsh((Hs+Hs.conj().T)/2)
EOF
echo done