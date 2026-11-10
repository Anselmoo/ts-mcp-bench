import numpy as np, itertools
from scipy.special import sph_harm
from scipy.sparse import csr_matrix, identity, kron, diags
from scipy.optimize import brentq

def Y(l,m,th,ph): return sph_harm(m,l,ph,th)
xg,wg = np.polynomial.legendre.leggauss(30)
phis = np.linspace(0,2*np.pi,60,endpoint=False)
TH,PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.ones_like(phis))*(2*np.pi/len(phis))
def ints(f): return np.sum(f*W)
sph = {m: Y(2,m,TH,PH) for m in range(-2,3)}
s2=np.sqrt(2)
cub = {
 'xy' : (sph[2]-sph[-2])/(1j*s2),
 'yz' : -(sph[1]+sph[-1])/s2,
 'xz' : (sph[1]-sph[-1])/(1j*s2),
 'z2' : sph[0],
 'x2y2': (sph[2]+sph[-2])/s2,
}
names=['xy','yz','xz','z2','x2y2']
eps_cf={'xy':-4,'yz':-4,'xz':-4,'z2':6,'x2y2':6}  # units of Dq
for a in names:
  for b in names:
    assert abs(ints(np.conj(cub[a])*cub[b]) - (a==b))<1e-9,(a,b)
# angular coefficients a_k(i,j,k,l) for <ij|1/r|kl>, with F^k weights
def ang(i,j,k,l):
    out={}
    for kk in (0,2,4):
        s=0
        for q in range(-kk,kk+1):
            Ykq=Y(kk,q,TH,PH)
            s += ints(np.conj(cub[i])*cub[k]*np.conj(Ykq))*ints(np.conj(cub[j])*cub[l]*Ykq)
        out[kk]=4*np.pi/(2*kk+1)*s
    return out
# Build one-electron and two-electron tensors over 10 spin-orbitals
so=[(o,s) for o in names for s in (0,1)]
n=len(so)
h=np.zeros((n,n))
for p,(o,s) in enumerate(so): h[p,p]=eps_cf[o]
# Racah parameters -> F2,F4 ; F0 irrelevant for d^6 energy differences (constant) except it's common
def solve(Dq,B,C=None):
    if C is None: C=4.5*B
    F4=441*C/35; F2=(441*B+5*F4)/9
    Fk={0:0.0,2:F2,4:F4}
    V=np.zeros((n,n,n,n))
    for p,(o1,s1) in enumerate(so):
     for q,(o2,s2_) in enumerate(so):
      for r,(o3,s3) in enumerate(so):
       for t,(o4,s4) in enumerate(so):
        # <pq|1/r|rt> spin: s1==s4 and s2==s3
        if s1!=s4 or s2_!=s3: continue
        a=ang(o1,o2,o3,o4)
        V[p,q,r,t]=sum(a[k]*Fk[k] for k in (2,4))
    return V
