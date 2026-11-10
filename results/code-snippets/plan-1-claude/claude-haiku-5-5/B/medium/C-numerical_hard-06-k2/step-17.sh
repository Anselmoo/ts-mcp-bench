cd /dev/shm && cat > sym.py <<'EOF'
from ts import *
from scipy.linalg import expm
from scipy.spatial.transform import Rotation as Rot
import itertools as it
# J matrices for l=2 in basis m=-2..2
L=2
Jz=np.diag([float(m) for m in ms]).astype(complex)
Jp=np.zeros((5,5),complex)
for i,m in enumerate(ms[:-1]):
    Jp[i+1,i]=np.sqrt(L*(L+1)-m*(m+1))
Jm=Jp.conj().T
Jx=(Jp+Jm)/2; Jy=(Jp-Jm)/(2j)
# O group: signed permutation matrices with det +1
Og=[]
for perm in it.permutations(range(3)):
    for signs in it.product([1,-1],repeat=3):
        M=np.zeros((3,3))
        for i,p in enumerate(perm): M[i,p]=signs[i]
        if np.linalg.det(M)>0: Og.append(M)
assert len(Og)==24
def Dl(R):
    rv=Rot.from_matrix(R).as_rotvec()
    th=np.linalg.norm(rv)
    if th<1e-12: return np.eye(5,dtype=complex)
    n=rv/th
    return expm(-1j*th*(n[0]*Jx+n[1]*Jy+n[2]*Jz))
def fock_rep(U):
    # U: 10x10 single-particle unitary; returns 210x210 Fock matrix
    M=np.zeros((210,210),complex)
    occs=[[i for i in range(10) if (s>>i)&1] for s in states]
    for J,oj in enumerate(occs):
        for I,oi in enumerate(occs):
            M[I,J]=np.linalg.det(U[np.ix_(oi,oj)])
    return M
def Lam(R):
    U=np.kron(Dl(R),np.eye(2))
    return fock_rep(U)
EOF
python3 -c "
from sym import *
B,C=1.0,4.0
Dq=2.0
H=build(Dq,B,C)
# invariance check on a couple of group elements
for R in [Og[5],Og[17]]:
    Lm=Lam(R)
    print('comm',np.abs(Lm@H-H@Lm).max(), 'unitary',np.abs(Lm.conj().T@Lm-np.eye(210)).max())
"