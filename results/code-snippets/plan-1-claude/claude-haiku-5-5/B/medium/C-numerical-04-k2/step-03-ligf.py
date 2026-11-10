import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
nth, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nth)
ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(np.arccos(x), ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
def Y(l,m): return sph_harm(m, l, PH, TH)
ms = [-2,-1,0,1,2]
Yd = [Y(2,m) for m in ms]
def integ(f): return np.sum(W*f)
def ak_table(kk):
    A = np.zeros((5,5,5,5),complex)
    for q in range(-kk,kk+1):
        Yq = Y(kk,q)
        G = np.array([[integ(np.conj(Yd[i])*np.conj(Yq)*Yd[k]) for k in range(5)] for i in range(5)])
        H = np.array([[integ(np.conj(Yd[j])*Yq*Yd[l]) for l in range(5)] for j in range(5)])
        A += np.einsum('ik,jl->ijkl', G, H)
    return A*4*np.pi/(2*kk+1)
A0,A2,A4 = ak_table(0),ak_table(2),ak_table(4)
# ensure 1/r12 expansion: V = sum_k F^k * A_k
def Vtensor(F2,F4):
    return A0*0 + F2*A2 + F4*A4   # F0 irrelevant for quartets (constant shift)
# real orbital transform for crystal field
X = np.sin(TH)*np.cos(PH); Yc = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
real_fun = {'xy':np.sqrt(15/(4*np.pi))*X*Yc, 'yz':np.sqrt(15/(4*np.pi))*Yc*Z,
            'zx':np.sqrt(15/(4*np.pi))*Z*X, 'z2':np.sqrt(5/(16*np.pi))*(3*Z**2-1),
            'x2y2':np.sqrt(15/(16*np.pi))*(X**2-Yc**2)}
names=['xy','yz','zx','z2','x2y2']
M = np.array([[integ(np.conj(Yd[j])*real_fun[n]) for j in range(5)] for n in names])
# M[r,j] = <Y_j|phi_r>; phi_r = sum_j conj(M[r,j])? check orthonormality
def field_single(Dq):
    # one-electron operator in complex basis: Vc = sum_r eps_r |phi_r><phi_r|
    eps=[-4*Dq]*3+[6*Dq]*2
    # |phi_r> coefficients in Y_j basis: c_rj = <Y_j|phi_r> = M[r,j]
    Vc = np.zeros((5,5),complex)
    for r in range(5):
        Vc += eps[r]*np.outer(np.conj(M[r]), M[r])  # |phi><phi| with phi_j = M[r,j]
    return Vc
if __name__=='__main__':
    print('orthonormality of real orbs:', np.round(np.abs(M@M.conj().T),6))
