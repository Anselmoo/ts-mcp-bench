import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
# quadrature on sphere
nth, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nth)
ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(np.arccos(x), ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
def Y(l,m): return sph_harm(m, l, PH, TH)   # scipy: sph_harm(m,n,azimuth,polar)
ms = [-2,-1,0,1,2]
Yd = [Y(2,m) for m in ms]
def integ(f): return np.sum(W*f)
# cubic field one-electron matrix in complex basis, via real t2g/eg construction
# real d orbitals as combos of complex Y_2m (orthonormal): build cubic field operator
# Use Oh: t2g = xy,yz,zx ; eg = z2, x2-y2 ; define via cartesian functions on sphere
X = np.sin(TH)*np.cos(PH); Yc = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
real_fun = {'xy':np.sqrt(15/(4*np.pi))*X*Yc, 'yz':np.sqrt(15/(4*np.pi))*Yc*Z,
            'zx':np.sqrt(15/(4*np.pi))*Z*X, 'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1),
            'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Yc**2)}
names=['xy','yz','zx','z2','x2y2']
# complex basis matrix: coefficients c[r,m] so that real_r = sum_m c[r,m] Y_m
M = np.zeros((5,5),complex)
for r,n in enumerate(names):
    for j,m in enumerate(ms):
        M[r,j] = integ(np.conj(Yd[j])*real_fun[n])
# Oh one-electron potential in real basis: t2g -4Dq, eg +6Dq
def field_complex(Dq):
    Vr = np.diag([-4*Dq]*3+[6*Dq]*2).astype(complex)
    # real orbitals phi_r = sum_j M[r,j] Y_j ; orthonormal -> Vc = M^H ... use: complex matrix Vc_{jk}=sum_r conj(M[r,j]) Vr[r,r] M[r,k]
    return M.conj().T @ Vr @ M
# angular coefficient a_k(i,j,k,l) = (4pi/(2k+1)) sum_q <i|Y_kq^*|k>... compute using complex basis
def Ykq(k,q): return Y(k,q)
def ak_table(kk):
    # returns A[i,j,k,l] = <ij|P_k|kl> angular part: int int conj(Yi)(1) conj(Yj)(2) P_k(12) Yk(1) Yl(2)
    # P_k = 4pi/(2k+1) sum_q conj(Y_kq(1)) Y_kq(2)  -> sum over q
    A = np.zeros((5,5,5,5),complex)
    # precompute single-particle integrals G[q][i,k] = int conj(Yi) conj(Ykq) Yk
    for q in range(-kk,kk+1):
        Yq = Ykq(kk,q)
        G = np.zeros((5,5),complex)  # G[i,k] = int conj(Yi)*conj(Yq)*Yk ... need careful
        for i in range(5):
            for kx in range(5):
                G[i,kx] = integ(np.conj(Yd[i])*np.conj(Yq)*Yd[kx])
        H = np.zeros((5,5),complex)
        for j in range(5):
            for l in range(5):
                H[j,l] = integ(np.conj(Yd[j])*Yq*Yd[l])
        A += np.einsum('ik,jl->ijkl', G, H)
    return A*4*np.pi/(2*kk+1)
