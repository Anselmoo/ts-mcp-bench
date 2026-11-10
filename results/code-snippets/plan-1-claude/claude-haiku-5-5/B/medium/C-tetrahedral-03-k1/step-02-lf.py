import numpy as np, itertools
from scipy.sparse import csr_matrix, identity, kron
from scipy.sparse.linalg import eigsh
from scipy.optimize import least_squares
from numpy.polynomial.legendre import leggauss

# angular quadrature on sphere
nt, nphi = 16, 32
xg, wg = leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
pts=[];w=[]
for ct,wt in zip(xg,wg):
    st=np.sqrt(1-ct*ct)
    for ph in phis:
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); w.append(wt*2*np.pi/nphi)
P=np.array(pts); W=np.array(w)
x,y,z=P.T
funcs=[x*y, y*z, z*x, x*x-y*y, 2*z*z-x*x-y*y]  # xy,yz,zx,x2-y2,z2
names=['xy','yz','zx','x2-y2','z2']
F=[]
for f in funcs:
    n=np.sum(W*f*f); F.append(f/np.sqrt(n))
F=np.array(F)  # 5 x Npts
# Legendre P_k(cos gamma) between pts: use matrix via dot products
cosg = P@P.T
from numpy.polynomial import legendre as L
def Pk(k,c): 
    coeffs=np.zeros(k+1); coeffs[k]=1
    return L.legval(c,coeffs)
Ak={}
for k in [0,2,4]:
    K=Pk(k,cosg)  # pts x pts
    # A[a,c,b,d] = sum_{i,j} F_a(i)F_c(i) W_i * K_ij * F_b(j)F_d(j) W_j
    G=np.einsum('ai,ci,i->aci',F,F,W)  # 5x5xN
    Ak[k]=np.einsum('aci,ij,bdj->acbd',G,K*W[None,:],G)  # careful weights
# Ak[k][a,c,b,d] = int int Y_a(1)Y_c(1) P_k Y_b(2) Y_d(2)
# so <ab|1/r|cd> with a(1)->c(1): V[a,b,c,d] = sum_k F_k * Ak[k][a,c,b,d]
def Vspatial(Fk):
    return sum(Fk[k]*Ak[k] for k in Fk)  # returns [a,c,b,d]

# Slater integrals from B,C: F2,F4 with F4/F2 chosen via C: B=(9F2-5F4)/441, C=35F4/441
def slater(B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    return {0:0.0,2:F2,4:F4}

# Fock space: 10 spin orbitals index = 2*orb + spin (spin 0 up, 1 down)
M=10
def cop(i):
    # annihilation on JW
    I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.]))
    a=csr_matrix(np.array([[0,1.],[0,0]]))  # annihilates |1>->|0>, basis (|0>,|1>)
    ops=[]
    mats=[]
    for j in range(M):
        mats.append(Z if j<i else (a if j==i else I2))
    out=mats[0]
    for m in mats[1:]: out=kron(out,m,format='csr')
    return out
c=[cop(i) for i in range(M)]
cd=[m.T.tocsr() for m in c]
# number operator check
# occupation basis: index bit ordering: state |n> with basis (|0>,|1>) where |1> occupied
Nop=sum(cd[i]@c[i] for i in range(M))
nd=Nop.diagonal()
sector=np.where(np.isclose(nd,8))[0]

def spin(s): return s  # s=0 up,1 down
def build_H(B,C,Dq):
    Fk=slater(B,C)
    V=Vspatial(Fk)
    # spin-orbital one-body
    h=np.zeros((10,10))
    # Td: t2 (xy,yz,zx) = +6Dq ; e (x2-y2,z2) = -4Dq
    eps=[6*Dq,6*Dq,6*Dq,-4*Dq,-4*Dq]
    H=csr_matrix((1024,1024))
    for o in range(5):
        for s in range(2):
            i=2*o+s
            H=H+eps[o]*(cd[i]@c[i])
    Hee=csr_matrix((1024,1024))
    for a in range(5):
     for b in range(5):
      for cc in range(5):
       for d in range(5):
        v=V[a,cc,b,d]
        if abs(v)<1e-12: continue
        for s in range(2):
         for t in range(2):
          # sum over spins: a s,c s' ... <ab|cd> with spin conservation: spin(a)=spin(c), spin(b)=spin(d)
          i=2*a+s; j=2*b+t; k=2*cc+s; l=2*d+t
          Hee=Hee+0.5*v*(cd[i]@cd[j]@c[l]@c[k])
    H=H+Hee
    return H
def levels(B,C,Dq):
    H=build_H(B,C,Dq)
    # Ms=1 sector: n_up=5,n_down=3
    up=[2*o for o in range(5)]; dn=[2*o+1 for o in range(5)]
    Nup=sum(cd[i]@c[i] for i in up).diagonal()
    Ndn=sum(cd[i]@c[i] for i in dn).diagonal()
    idx=np.where(np.isclose(Nup,5)&np.isclose(Ndn,3))[0]
    Hs=H[idx][:,idx].toarray()
    return np.sort(np.linalg.eigvalsh(Hs))
if __name__=='__main__':
    # test: Oh-like check via pure Dq-only: levels
    ev=levels(1000.,4000.,0.)
    print(np.round(ev,3))
