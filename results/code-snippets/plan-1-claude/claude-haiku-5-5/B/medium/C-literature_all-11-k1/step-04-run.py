import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.sparse import csr_matrix, identity, kron, diags
from scipy.optimize import brentq
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
# Fock operators for N=6 in 10 modes
I2=identity(2,format='csr'); Z=diags([1,-1]).tocsr()
a=csr_matrix(np.array([[0,1],[0,0]]))  # annihilation: |1>->|0>; basis (0=empty,1=occ)? use basis [|0>,|1>]
ann=csr_matrix(np.array([[0,1],[0,0]],dtype=float))
cre=ann.T.tocsr()
def op(i,local):
    m=identity(1,format='csr')
    for j in range(n):
        if j<i: m=kron(m,Z,format='csr')
        elif j==i: m=kron(m,local,format='csr')
        else: m=kron(m,I2,format='csr')
    return m
Cr=[op(i,cre) for i in range(n)]
An=[op(i,ann) for i in range(n)]
# occupation sector N=6
Nop=sum(Cr[i]@An[i] for i in range(n))
dN=Nop.diagonal()
idx=np.where(np.isclose(dN,6))[0]
def restrict(M): return M[idx][:,idx]
Cr_r=[None]*n
def build(Dq,B,C):
    F4=441*C/35; F2=(441*B+5*F4)/9
    Fk={2:F2,4:F4}
    H=csr_matrix((len(idx),len(idx)))
    for p in range(n):
        if eps_cf[so[p][0]]!=0:
            H=H+eps_cf[so[p][0]]*Dq*restrict(Cr[p]@An[p])
    for (p,q,r,t),a_ in A.items():
        v=sum(a_[k]*Fk[k] for k in (2,4))
        if abs(v)>1e-14:
            H=H+0.5*v*restrict(Cr[p]@Cr[q]@An[t]@An[r])
    return H.toarray()
# total spin S^2 check via Sz and S+S-
def levels(Dq,B,C=None):
    if C is None: C=4.5*B
    H=build(Dq,B,C)
    # add S^2 penalty to isolate singlets
    Sz=np.zeros(len(idx)); 
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build S+ = sum c†_up c_down
    Sp=csr_matrix((len(idx),len(idx)))
    for o in names:
        Sp=Sp+restrict(Cr[so.index((o,0))]@An[so.index((o,1))])
    Sp=Sp.toarray()
    Sz=np.array([ (dN_up:=0) for _ in range(len(idx))])
    S2=Sp@Sp.T  # S- S+ ... S^2 = S-S+ + Sz(Sz+1); Sp.T = S-
    # compute S^2 = S- S+ + Sz^2 + Sz with Sz=(N_up-N_dn)/2 ; for N=6 total: diag
    Nup=np.zeros(len(idx))
    for p in range(n):
        if so[p][1]==0: Nup+=restrict(Cr[p]@An[p]).diagonal()
    Ndn=6-Nup
    Szv=(Nup-Ndn)/2
    S2=Sp.T@Sp+np.diag(Szv*(Szv+1)) if False else Sp.T@Sp + np.diag(Szv**2+Szv)
    # Sp applies S+ ; S- S+ = Sp.T? S+ = Sp, S- = Sp.T ; S^2 = S-S+ + Sz^2+Sz
    lam=1e4
    w,v=np.linalg.eigh(H+lam*S2)
    E=[];
    for ev,vec in zip(w,v.T):
        s2v=vec@S2@vec
        if abs(s2v)<0.5: E.append(ev)
    E=np.array(sorted(E))
    return E
if __name__=="__main__":
    E=levels(0.0,1.0)
    print(np.round(E[:20],4), len(E))
