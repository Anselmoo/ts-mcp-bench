cd /tmp && python3 - << 'EOF'
import numpy as np
from scipy.special import sph_harm_y
from scipy.sparse import csr_matrix, identity, kron, diags
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
for a in names:
  for b in names:
    assert abs(ints(np.conj(cub[a])*cub[b])-(a==b))<1e-9
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
print("dim",len(idx))
R=lambda M: M[idx][:,idx]
CA=[[R(Cr[p]@An[q]) for q in range(n)] for p in range(n)]
# two-body operators precomputed for needed quadruples
CCAA={}
def ccaa(p,q,r,t):
    key=(p,q,r,t)
    if key not in CCAA:
        CCAA[key]=R(Cr[p]@Cr[q]@An[t]@An[r])
    return CCAA[key]
# spin ops
Sp=sum((CA[o][o+0]*0 for o in []), 0)
Spm=csr_matrix((len(idx),len(idx)))
for o in names:
    Spm=Spm+CA[so.index((o,0))][so.index((o,1))]
Spm=Spm.toarray()
Nup=np.zeros(len(idx))
for p in range(n):
    if so[p][1]==0: Nup+=CA[p][p].diagonal()
Szv=(Nup-(6-Nup))/2
S2=Spm.T@Spm+np.diag(Szv**2+Szv)   # S-S+ + Sz^2+Sz
diag_cf=[sum(eps_cf[so[p][0]]*CA[p][p].toarray() for p in range(n))]
Hcf=sum(eps_cf[so[p][0]]*CA[p][p].toarray() for p in range(n))
# Coulomb tensors: keep only nonzero
terms=[]
for (p,q,r,t),a_ in A.items():
    if abs(a_[2])>1e-12 or abs(a_[4])>1e-12:
        terms.append((p,q,r,t,a_[2],a_[4]))
print("nonzero coulomb terms",len(terms))
Ccoul={}
for (p,q,r,t,a2,a4) in terms:
    Ccoul[(p,q,r,t)]=(a2,a4, ccaa(p,q,r,t).toarray())
def levels(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    H=Dq*Hcf.copy()
    for (p,q,r,t),(a2,a4,M) in Ccoul.items():
        H+=0.5*(a2*F2+a4*F4)*M
    w,v=np.linalg.eigh(H+1e4*S2)
    E=[]; 
    for ev,vec in zip(w,v.T):
        if abs(vec@S2@vec)<0.5: E.append(ev)
    return np.array(sorted(E))
import sys
E=levels(0.0,1.0,4.5)
print(np.round(E[:12],3),len(E))
EOF