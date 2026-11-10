mkdir -p /w && cat > /w/lf.py << 'EOF'
import numpy as np
from scipy.special import sph_harm
from itertools import combinations
from scipy.optimize import least_squares

# angular grid
nt, nphi = 40, 80
x, wt = np.polynomial.legendre.leggauss(nt)
theta = np.arccos(x); phi = np.linspace(0, 2*np.pi, nphi, endpoint=False)
TH, PH = np.meshgrid(theta, phi, indexing='ij')
W = np.outer(wt, np.full(nphi, 2*np.pi/nphi))
def Y(l, m): return sph_harm(m, l, PH, TH)  # scipy: (m, n, azimuth, polar)
ms = [-2,-1,0,1,2]
Yd = {m: Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)

# Coulomb angular factors A[k][a,c,b,d] = sum_q 4pi/(2k+1) <a|Y*kq|c><b|Ykq|d>
def Ykq(k,q): return Y(k,q)
Ak = {}
for k in (2,4):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Ykk = Ykq(k,q)
        M1 = np.zeros((5,5), complex); M2 = np.zeros((5,5), complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                M1[i,j] = integ(np.conj(Yd[a])*np.conj(Ykk)*Yd[c])
                M2[i,j] = integ(np.conj(Yd[a])*Ykk*Yd[c])
        # <a|Y*kq|c> = M1[a,c]; <b|Ykq|d> = M2[b,d]
        A += 4*np.pi/(2*k+1) * np.einsum('ac,bd->acbd', M1, M2)
    Ak[k] = A

# one-body Oh field (electron), real d orbitals in m basis
def cvec(d):  # dict m->coef
    v = np.zeros(5, complex)
    for m,c in d.items(): v[ms.index(m)] = c
    return v
s2 = np.sqrt(2)
orbs_eg = [cvec({-2:1/s2, 2:1/s2}), cvec({0:1})]
orbs_t2 = [cvec({-2:1j/s2, 2:-1j/s2}), cvec({-1:-1/s2, 1:1/s2}), cvec({-1:1j/s2, 1:1j/s2})]
def hfield(Dq):  # Oh: eg +6Dq, t2g -4Dq
    h = np.zeros((5,5), complex)
    for v in orbs_eg: h += 6*Dq*np.outer(v, v.conj())
    for v in orbs_t2: h += -4*Dq*np.outer(v, v.conj())
    return h

# Fock space, 5 spin-orbitals, JW
nmode = 5
def op_a(i):
    dim = 2**nmode; M = np.zeros((dim,dim))
    for s in range(dim):
        if (s>>i)&1:
            sign = (-1)**bin(s & ((1<<i)-1)).count('1')
            M[s ^ (1<<i), s] = sign
    return M
a = [op_a(i) for i in range(nmode)]
ad = [x.T for x in a]
# restrict to N=3
Nop = sum(ad[i]@a[i] for i in range(nmode))
idx = [s for s in range(2**nmode) if bin(s).count('1')==3]
P = np.zeros((2**nmode, len(idx)))
for j,s in enumerate(idx): P[s,j]=1

def build(Dq, F2, F4):
    F = {2:F2, 4:F4}
    h = hfield(Dq)
    H1 = sum(h[i,j]*ad[i]@a[j] for i in range(5) for j in range(5))
    V = np.zeros((5,5,5,5), complex)
    for k in (2,4): V += F[k]*Ak[k]   # V[a,c,b,d] = <ab|1/r|cd>
    # H2 = 1/2 sum V_abcd a+_a a+_b a_d a_c, with <ab|V|cd>: indices (a,b,c,d)
    H2 = np.zeros_like(H1)
    for A_ in range(5):
     for B_ in range(5):
      for C_ in range(5):
       for D_ in range(5):
        v = V[A_,C_,B_,D_]
        if abs(v)>1e-12:
            H2 += 0.5*v*(ad[A_]@ad[B_]@a[D_]@a[C_])
    H = (P.T@(H1+H2)@P)
    return H

def B_of(F2,F4): return (9*F2-5*F4)/441

if __name__ == "__main__":
    F2, F4 = 1.0, 0.625
    H = build(0.0, F2, F4)
    H = (H+H.conj().T)/2
    ev = np.linalg.eigvalsh(H)
    print("free-ion quartet levels (units F2):", np.round(ev - ev[0],5))
    B = B_of(F2,F4)
    print("B=",B, " gap/B:", np.round((ev-ev[0])/B,4))
EOF
cd /w && python3 lf.py