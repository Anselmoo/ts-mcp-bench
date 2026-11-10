
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from scipy.sparse import csr_matrix, identity, kron
from scipy.special import sph_harm
from scipy.optimize import brentq
from scipy.sparse.linalg import eigsh

# spin-orbitals: index = 2*orb + s ; orb 0..4 = m=-2..2 (spherical), s=0 up,1 down
# Build cubic orbitals as combos of Y_2m (cubic basis: t2g, eg)
def Y(l,m,th,ph): return sph_harm(m,l,ph,th)   # scipy: sph_harm(m,n,azimuth,polar)
# grid
xg,wg = np.polynomial.legendre.leggauss(30)
phis = np.linspace(0,2*np.pi,60,endpoint=False)
TH,PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.ones_like(phis))*(2*np.pi/len(phis))
def ints(f): return np.sum(f*W)
# spherical basis m=-2..2
sph = {m: Y(2,m,TH,PH) for m in range(-2,3)}
# cubic orbitals (complex combos, orthonormal)
s2=np.sqrt(2)
cub = {
 'xy' : (sph[2]-sph[-2])/(1j*s2),
 'yz' : (sph[1]+sph[-1])/(-s2)*1.0,
 'xz' : (sph[1]-sph[-1])/(1j*s2),
 'z2' : sph[0],
 'x2y2': (sph[2]+sph[-2])/s2,
}
# cubic-basis orbitals: t2g = xy,yz,xz ; eg = z2,x2y2
names=['xy','yz','xz','z2','x2y2']
energy={'xy':-4,'yz':-4,'xz':-4,'z2':6,'x2y2':6}  # in units of Dq
for a in names:
  for b in names:
    assert abs(ints(np.conj(cub[a])*cub[b]) - (a==b))<1e-9, (a,b)
norb=5
# angular coefficients: A[k][(i,k_),q] integrals
def angcoef(i,j,k,l):
    # sum_k (4pi/(2k+1)) sum_q (∫ conj(phi_i) phi_j Y_kq^*)(∫ conj(phi_k) phi_l Y_kq)
    # careful: <ij|1/r|kl> = ∫∫ phi_i*(1) phi_j*(2) phi_k(1) phi_l(2)/r12
    res={}
    for kk in (0,2,4):
        s=0
        for q in range(-kk,kk+1):
            Ykq=Y(kk,q,TH,PH)
            s += ints(np.conj(cub[names[i]])*cub[names[k]]*np.conj(Ykq)) * ints(np.conj(cub[names[j]])*cub[names[l]]*Ykq)
        res[kk]= 4*np.pi/(2*kk+1)*s
    return res
EOF
echo ok