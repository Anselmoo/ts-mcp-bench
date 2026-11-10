
cat << 'EOF' | python3 -
import numpy as np
from scipy.special import sph_harm
nth, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = list(range(-2,3))
Ylm = {m: sph_harm(m,2,PH,TH) for m in ms}
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Yq = sph_harm(q,k,PH,TH)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A
A = {k: ang_k(k) for k in (0,2,4)}
print("imag max", max(np.abs(A[k].imag).max() for k in A))
# check: F0 coefficient diagonal <ab|ab> for a=b should be 1 (F0 coeff for same orbital)
print("A0[0,0,0,0]", A[0][0,0,0,0].real, "A2 diag sample", A[2][2,2,2,2].real, A[4][2,2,2,2].real)
# Save angular tensors as python literal into stdout? keep in memory: just recompute in one script
import pickle
EOF
