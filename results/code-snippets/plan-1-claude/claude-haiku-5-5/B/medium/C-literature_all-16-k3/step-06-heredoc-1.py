import numpy as np
from scipy.special import sph_harm_y as SY
from scipy.optimize import least_squares
nth, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = list(range(-2,3))
Ylm = {m: SY(2,m,TH,PH) for m in ms}
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Yq = SY(k,q,TH,PH)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A
A = {k: ang_k(k) for k in (0,2,4)}
print("imag max", max(np.abs(A[k].imag).max() for k in A))
print("A0 00 00", A[0][0,0,0,0].real, "A2 22 22", A[2][2,2,2,2].real, A[4][2,2,2,2].real)
np.savez('/dev/shm/ang.npz', A0=A[0].real, A2=A[2].real, A4=A[4].real)
