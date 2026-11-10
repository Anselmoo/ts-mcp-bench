import numpy as np
from scipy.sparse import csr_matrix, identity, kron
from numpy.polynomial.legendre import leggauss
from numpy.polynomial import legendre as L
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
funcs=[x*y, y*z, z*x, x*x-y*y, 2*z*z-x*x-y*y]
F=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
cosg=np.clip(P@P.T,-1,1)
def Pk(k,c):
    co=np.zeros(k+1); co[k]=1; return L.legval(c,co)
G=np.einsum('ai,ci,i->aci',F,F,W)
Ak={k:np.einsum('aci,ij,bdj->acbd',G,Pk(k,cosg),G) for k in [0,2,4]}
M=10
I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.])); am=csr_matrix(np.array([[0,1.],[0,0]]))
def cop(i):
    mats=[Z if j<i else (am if j==i else I2) for j in range(M)]
    out=mats[0]
    for m in mats[1:]: out=kron(out,m,format='csr')
    return out
c=[cop(i) for i in range(M)]
cd=[m.T.tocsr() for m in c]
num=[cd[i]@c[i] for i in range(M)]
# precompute two-body terms
terms=[]
for a in range(5):
 for b in range(5):
  for cc in range(5):
   for d in range(5):
    for s in range(2):
     for t in range(2):
      i=2*a+s; j=2*b+t; k=2*cc+s; l=2*d+t
      terms.append((a,cc,b,d,0.5*cd[i]@cd[j]@c[l]@c[k]))
def build_H(B,C,Dq):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    Fk={0:0.0,2:F2,4:F4}
    V=sum(Fk[k]*Ak[k] for k in Fk)
    eps=[6*Dq]*3+[-4*Dq]*2
    H=csr_matrix((1024,1024))
    for o in range(5):
        for s in range(2): H=H+eps[o]*num[2*o+s]
    for (a,cc,b,d,op) in terms:
        v=V[a,cc,b,d]
        if abs(v)>1e-10: H=H+v*op
    return H
up=[2*o for o in range(5)]; dn=[2*o+1 for o in range(5)]
Nup=sum(num[i] for i in up).diagonal(); Ndn=sum(num[i] for i in dn).diagonal()
idx=np.where(np.isclose(Nup,5)&np.isclose(Ndn,3))[0]
Nt=sum(num).diagonal(); idx8=np.where(np.isclose(Nt,8))[0]
def levels(B,C,Dq):
    H=build_H(B,C,Dq)
    Hs=H[idx][:,idx].toarray()
    return np.sort(np.linalg.eigvalsh(Hs))
print(len(idx))
# check free ion: Dq=0 levels
ev=levels(1000.,4000.,0.)
print(np.round(ev,2))
