from ts import *
from scipy.linalg import expm, null_space
from scipy.spatial.transform import Rotation as Rot
import itertools as it
L=2
Jz=np.diag([float(m) for m in ms]).astype(complex)
Jp=np.zeros((5,5),complex)
for i,m in enumerate(ms[:-1]):
    Jp[i+1,i]=np.sqrt(L*(L+1)-m*(m+1))
Jm=Jp.conj().T
Jx=(Jp+Jm)/2; Jy=(Jp-Jm)/(2j)
Og=[]
for perm in it.permutations(range(3)):
    for signs in it.product([1,-1],repeat=3):
        M=np.zeros((3,3))
        for i,p in enumerate(perm): M[i,p]=signs[i]
        if np.linalg.det(M)>0: Og.append(M)
def Dl(R):
    rv=Rot.from_matrix(R).as_rotvec()
    th=np.linalg.norm(rv)
    if th<1e-12: return np.eye(5,dtype=complex)
    n=rv/th
    return expm(-1j*th*(n[0]*Jx+n[1]*Jy+n[2]*Jz))
occs=[[i for i in range(10) if (s>>i)&1] for s in states]
def fock_rep(U):
    M=np.zeros((210,210),complex)
    for J,oj in enumerate(occs):
        for I,oi in enumerate(occs):
            M[I,J]=np.linalg.det(U[np.ix_(oi,oj)])
    return M
def Lam(R):
    return fock_rep(np.kron(Dl(R),np.eye(2)))
