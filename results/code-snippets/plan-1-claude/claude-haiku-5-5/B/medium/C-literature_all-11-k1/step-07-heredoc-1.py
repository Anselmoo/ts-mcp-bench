import numpy as np
from scipy.special import sph_harm_y
from scipy.sparse import csr_matrix, identity, kron, diags
from scipy.optimize import fsolve
def Y(l,m,th,ph): return sph_harm_y(l,m,th,ph)
xg,wg = np.polynomial.legendre.leggauss(30)
phis = np.linspace(0,2*np.pi,60,endpoint=False)
TH,PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.ones_like(phis))*(2*np.pi/len(phis))
def ints(f): return np.sum(f*W)
sph = {m: Y(2,m,TH,PH) for m in range(-2,3)}
s2=np.sqrt(2)
cub = {'xy':(sph[2]-sph[-2])/(1j*s2),'yz':-(sph[1]+sph[-1])/s2,'xz':(sph[1]-sph[-1])/(1j*s2),
       'z2':sph[0],'x2y2':(sph[2]+sph[-2])/s2}
names=['xy','yz','xz','z2','x2y2']
eps_cf={'xy':-4,'yz':-4,'xz':-4,'z2':6,'x2y2':6}
Ykqs={(k,q):Y(k,q,TH,PH) for k in (2,4) for q in range(-k,k+1)}
def ang(i,j,k,l):
    out={}
    for kk in (2,4):
        s=0
        for q in range(-kk,kk+1):
            Ykq=Ykqs[(kk,q)]
            s+=ints(np.conj(cub[i])*cub[k]*np.conj(Ykq))*ints(np.conj(cub[j])*cub[l]*Ykq)
        out[kk]=(4*np.pi/(2*kk+1)*s).real
    return out
so=[(o,s) for o in names for s in (0,1)]
n=len(so)
A={}
for p,(o1,s1) in enumerate(so):
 for q,(o2,s2_) in enumerate(so):
  for r,(o3,s3) in enumerate(so):
   for t,(o4,s4) in enumerate(so):
    if s1==s4 and s2_==s3:
      A[(p,q,r,t)]=ang(o1,o2,o3,o4)
I2=identity(2,format='csr'); Z=diags([1.,-1.]).tocsr()
ann=csr_matrix(np.array([[0,1],[0,0]],dtype=float)); cre=ann.T.tocsr()
def op(i,local):
    m=identity(1,format='csr')
    for j in range(n):
        m=kron(m, Z if j<i else (local if j==i else I2), format='csr')
    return m
Cr=[op(i,cre) for i in range(n)]; An=[op(i,ann) for i in range(n)]
Nop=sum((Cr[i]@An[i]).diagonal() for i in range(n))
idx=np.where(np.isclose(Nop,6))[0]
R=lambda M: M[idx][:,idx]
CA=[[R(Cr[p]@An[q]) for q in range(n)] for p in range(n)]
Spm=sum(CA[so.index((o,0))][so.index((o,1))] for o in names).toarray()
Nup=sum(CA[p][p].diagonal() for p in range(n) if so[p][1]==0)
Szv=(Nup-(6-Nup))/2
S2=Spm.T@Spm+np.diag(Szv**2+Szv)
Hcf=sum(eps_cf[so[p][0]]*CA[p][p].toarray() for p in range(n))
Ccoul=[]
for (p,q,r,t),a_ in A.items():
    if abs(a_[2])>1e-12 or abs(a_[4])>1e-12:
        M=R(Cr[p]@Cr[q]@An[t]@An[r]).toarray()
        Ccoul.append((a_[2],a_[4],M))
M2=sum(0.5*a2*M for a2,a4,M in Ccoul)  # F2 coefficient
M4=sum(0.5*a4*M for a2,a4,M in Ccoul)  # F4 coefficient
def levels(Dq,B,C=None):
    if C is None: C=4.5*B
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=Dq*Hcf+F2*M2+F4*M4
    w,v=np.linalg.eigh(H+1e4*S2)
    E=[ev for ev,vec in zip(w,v.T) if abs(vec@S2@vec)<0.5]
    return np.array(sorted(E))
def triplets(E,tol=0.5):
    out=[];i=0
    while i<len(E):
        j=i
        while j+1<len(E) and abs(E[j+1]-E[i])<tol: j+=1
        out.append((E[i],j-i+1)); i=j+1
    return out
# Check free ion singlet terms
E=levels(0,1.0)
print("free ion (B=1,C=4.5) singlet levels:",[(round(e,3),d) for e,d in triplets(E)])
# Weak-field check Dq: singlet levels for Dq=2,B=0.5
E=levels(2.0,0.5)
print("Dq=2 B=0.5:",[(round(e-E[0],3),d) for e,d in triplets(E)][:10])
