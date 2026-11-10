cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np
from scipy.special import sph_harm
from scipy.optimize import least_squares
nth, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nth)
ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(np.arccos(x), ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
def Y(l,m): return sph_harm(m, l, PH, TH)
ms=[-2,-1,0,1,2]
Yd=[Y(2,m) for m in ms]
def integ(f): return np.sum(W*f)
def ak(kk):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-kk,kk+1):
        Yq=Y(kk,q)
        G=np.array([[integ(np.conj(Yd[i])*np.conj(Yq)*Yd[k]) for k in range(5)] for i in range(5)])
        H=np.array([[integ(np.conj(Yd[j])*Yq*Yd[l]) for l in range(5)] for j in range(5)])
        A+=np.einsum('ik,jl->ijkl',G,H)
    return A*4*np.pi/(2*kk+1)
A2=ak(2); A4=ak(4)
# check: complex Y orthonormal
print(np.round(np.array([[integ(np.conj(Yd[i])*Yd[j]) for j in range(5)] for i in range(5)]).real,6))
# Slater-Condon via determinants: spin orbitals index p = 2*orb + s (s=0 up,1 down)
F2,F4=1.0,0.625
Vint = F2*A2 + F4*A4   # <ij|1/r|kl> with orbital indices
dets=[]
# M_S=3/2 sector: 5 up electrons (all orbitals up) + 2 down electrons
for down in itertools.combinations(range(5),2) if False else []:
    pass
import itertools
dets=[]
for dn in itertools.combinations(range(5),2):
    occ=frozenset([(o,0) for o in range(5)]+[(o,1) for o in dn])
    dets.append(tuple(sorted(occ)))
print(len(dets))
EOF