import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq
# sphere quadrature
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(np.arccos(x), phis, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
def Y(l,m): return sph_harm(m, l, PH, TH)  # scipy: sph_harm(m,n,azimuth,polar)
ms = list(range(-2,3))
orb = [(m,s) for m in ms for s in (1,-1)]  # spin-orbitals index
# angular integrals M[k][q][a,c] = int Y_a^* Y_kq^* Y_c
def ang(k,q,a,c):
    return np.sum(W*np.conj(Y(2,a))*np.conj(Y(k,q))*Y(2,c))
def ang2(k,q,b,d):
    return np.sum(W*np.conj(Y(2,b))*Y(k,q)*Y(2,d))
def Vang(k,a,b,c,d):  # <ab|Y_k^*|cd> form: sum_q <a|Y*kq|c><b|Ykq|d>
    s=0
    for q in range(-k,k+1):
        if abs(q)>2: continue
        s+= ang(k,q,a,c)*ang2(k,q,b,d)
    return s
def build_V(F):  # F dict k->value, returns V[i,j,k,l] = <ij|1/r|kl> over spin-orbitals
    n=10; V=np.zeros((n,n,n,n),complex)
    for i,(m1,s1) in enumerate(orb):
        for j,(m2,s2) in enumerate(orb):
            for kk,(m3,s3) in enumerate(orb):
                for l,(m4,s4) in enumerate(orb):
                    if s1!=s3 or s2!=s4: continue
                    val=0
                    for k in (0,2,4):
                        val+= 4*np.pi/(2*k+1)*F[k]*Vang(k,m1,m2,m3,m4)
                    V[i,j,kk,l]=val
    return V
