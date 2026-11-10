python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
ms=[-2,-1,0,1,2]
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
Y=lambda l,m,th,ph: sph_harm_y(l,m,th,ph)
D=[Y(2,m,TH,PH) for m in ms]
ANG={}
for k in [2,4]:
    G=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(D[a])*D[c]*np.conj(Ykq)) for c in range(5)] for a in range(5)])
        Bm=np.array([[np.sum(W*np.conj(D[b])*D[d]*Ykq) for d in range(5)] for b in range(5)])
        G+=np.einsum('ac,bd->acbd',A,Bm)
    ANG[k]=G*4*np.pi/(2*k+1)
# check: F^0 limit: sum_{a,b} <ab|1/r|ab>-type; test k=0 analog not used. Check known: <d0 d0|1/r|d0 d0> angular = F0 coefficient...
# Known Slater: for d2 (m=2,m'=-2)? Compare Ak for k=2 with known a_k values: <2 0|...> skip
# Instead test: sum over ordered pairs gives known result; print ANG2 for a=c=b=d=2 (m=0)
print("G2[m0,m0,m0,m0]",ANG[2][2,2,2,2].real, " G4",ANG[4][2,2,2,2].real)
# Known: F0 for same orbital e_ii = 1; F2 angular coefficient for d^2 (m=2,-2) ~ 2/7? quick check of k=0 analog:
# Jeff: direct J(0,0) = F0 => a0 = 1. check via k=0 construction
G0=np.zeros((5,5,5,5),complex)
Y00=Y(0,0,TH,PH)
A=np.array([[np.sum(W*np.conj(D[a])*D[c]*np.conj(Y00)) for c in range(5)] for a in range(5)])
print("k0 G[a,a,b,b] (should be 1 for all a,b):", np.round(np.array([[A[a,a]*A[b,b]*4*np.pi for b in range(5)] for a in range(5)]).real,4))
EOF