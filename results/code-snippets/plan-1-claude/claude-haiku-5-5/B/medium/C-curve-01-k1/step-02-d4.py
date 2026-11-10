import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import expm, eigh
from scipy.sparse import csr_matrix, lil_matrix
B=821.0; C=3657.0
F4=63*C/5; F2=(441*B+5*F4)/9
Fk={2:F2,4:F4}
# quadrature
xg,wg=np.polynomial.legendre.leggauss(16)
nphi=32
phi=np.arange(nphi)*2*np.pi/nphi; wphi=2*np.pi/nphi
TH=np.arccos(xg)
TT,PP=np.meshgrid(TH,phi,indexing='ij'); W=np.outer(wg,np.ones(nphi))*wphi
def Y(l,m,th,ph): return sph_harm(m,l,ph,th)
ms=list(range(-2,3))
# orbitals: index 2*(m+2)+s  s=0 up,1 down
orbs=[(m,s) for m in ms for s in (0,1)]
N=len(orbs)
def ang(k,m1,m3,m2,m4):
    # electron1: m1<-m3 ; electron2: m2<-m4 ; sum over q
    tot=0
    for q in range(-k,k+1):
        G1=np.sum(W*np.conj(Y(2,m1,TT,PP))*np.conj(Y(k,q,TT,PP))*Y(2,m3,TT,PP))
        G2=np.sum(W*np.conj(Y(2,m2,TT,PP))*Y(k,q,TT,PP)*Y(2,m4,TT,PP))
        tot+=G1*G2
    return 4*np.pi/(2*k+1)*tot
# two-body tensor g[a,b,c,d] = <ab|1/r|cd>  (a,c electron1; b,d electron2)
g=np.zeros((N,N,N,N),dtype=complex)
for a,(m1,s1) in enumerate(orbs):
  for b,(m2,s2) in enumerate(orbs):
    for c,(m3,s3) in enumerate(orbs):
      for d,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4: continue
        val=0
        for k in (2,4):
            val+=Fk[k]*ang(k,m1,m3,m2,m4)
        # k=0 part is constant (F0 ignored)
        g[a,b,c,d]=val
# Fock space
dim=2**N
def bit(st,i): return (st>>i)&1
def cdag_c(i,j):
    # operator c_i^dag c_j on Fock basis (sparse)
    rows=[];cols=[];vals=[]
    for st in range(dim):
        if bit(st,j)==0: continue
        s1=st ^ (1<<j)
        sign=(-1)**bin(s1 & ((1<<j)-1)).count('1')
        if bit(s1,i)==1: continue
        s2=s1 | (1<<i)
        sign*= (-1)**bin(s2 & ((1<<i)-1)).count('1')
        rows.append(s2);cols.append(st);vals.append(sign)
    return csr_matrix((vals,(rows,cols)),shape=(dim,dim))
CC={}
def cd(i,j):
    if (i,j) not in CC: CC[(i,j)]=cdag_c(i,j)
    return CC[(i,j)]
# number of electrons
Nop=sum(cd(i,i) for i in range(N))
nel=np.array([bin(s).count('1') for s in range(dim)])
idx=np.where(nel==4)[0]
def restrict(M): return M[idx][:,idx].toarray()
# Electron repulsion: 1/2 sum g[a,b,c,d] c^+_a c^+_b c_d c_c
Hee=np.zeros((len(idx),len(idx)),dtype=complex)
Mcache={}
for a in range(N):
  for b in range(N):
    for c in range(N):
      for d in range(N):
        if abs(g[a,b,c,d])<1e-12: continue
        op=cd(a,c)@cd(b,d) if False else None
        # c+_a c+_b c_d c_c = (c+_a c+_b) (c_d c_c)
        M=(cd(a,a)*0)  # placeholder
        break
