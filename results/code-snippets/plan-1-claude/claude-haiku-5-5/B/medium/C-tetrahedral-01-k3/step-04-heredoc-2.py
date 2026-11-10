import numpy as np
from scipy.special import sph_harm
nt, nphi = 40, 80
x, wt = np.polynomial.legendre.leggauss(nt)
theta = np.arccos(x); phi = np.linspace(0, 2*np.pi, nphi, endpoint=False)
TH, PH = np.meshgrid(theta, phi, indexing='ij')
W = np.outer(wt, np.full(nphi, 2*np.pi/nphi))
def Y(l, m): return sph_harm(m, l, PH, TH)
ms = [-2,-1,0,1,2]
Yd = {m: Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
Ak = {}
for k in (2,4):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Ykk = Y(k,q)
        M1 = np.zeros((5,5), complex); M2 = np.zeros((5,5), complex)
        for i,a_ in enumerate(ms):
            for j,c in enumerate(ms):
                M1[i,j] = integ(np.conj(Yd[a_])*np.conj(Ykk)*Yd[c])
                M2[i,j] = integ(np.conj(Yd[a_])*Ykk*Yd[c])
        A += 4*np.pi/(2*k+1) * np.einsum('ac,bd->acbd', M1, M2)
    Ak[k] = A
def cvec(d):
    v = np.zeros(5, complex)
    for m,c in d.items(): v[ms.index(m)] = c
    return v
s2 = np.sqrt(2)
orbs_eg = [cvec({-2:1/s2, 2:1/s2}), cvec({0:1})]
orbs_t2 = [cvec({-2:1j/s2, 2:-1j/s2}), cvec({-1:-1/s2, 1:1/s2}), cvec({-1:1j/s2, 1:1j/s2})]
def hfield(Dq):
    h = np.zeros((5,5), complex)
    for v in orbs_eg: h += 6*Dq*np.outer(v, v.conj())
    for v in orbs_t2: h += -4*Dq*np.outer(v, v.conj())
    return h
nmode = 5
def op_a(i):
    dim = 2**nmode; M = np.zeros((dim,dim))
    for s in range(dim):
        if (s>>i)&1:
            sign = (-1)**bin(s & ((1<<i)-1)).count('1')
            M[s ^ (1<<i), s] = sign
    return M
a = [op_a(i) for i in range(nmode)]
ad = [x_.T for x_ in a]
idx = [s for s in range(2**nmode) if bin(s).count('1')==3]
P = np.zeros((2**nmode, len(idx)))
for j,s in enumerate(idx): P[s,j]=1
def build(Dq, F2, F4):
    F = {2:F2, 4:F4}
    h = hfield(Dq)
    H1 = sum(h[i,j]*ad[i]@a[j] for i in range(5) for j in range(5))
    V = np.zeros((5,5,5,5), complex)
    for k in (2,4): V += F[k]*Ak[k]
    H2 = np.zeros_like(H1)
    for A_ in range(5):
     for B_ in range(5):
      for C_ in range(5):
       for D_ in range(5):
        v = V[A_,C_,B_,D_]
        if abs(v)>1e-12:
            H2 += 0.5*v*(ad[A_]@ad[B_]@a[D_]@a[C_])
    return P.T@(H1+H2)@P
def B_of(F2,F4): return (9*F2-5*F4)/441
F2, F4 = 1.0, 0.625
H = build(0.0, F2, F4)
H = (H+H.conj().T)/2
ev = np.linalg.eigvalsh(H)
B = B_of(F2,F4)
print("levels/B:", np.round((ev-ev[0])/B,4))
print("F2/B", F2/B)
