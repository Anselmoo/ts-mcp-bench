python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
def sph_harm(m, l, azim, polar): return sph_harm_y(l, m, polar, azim)
xg, wg = np.polynomial.legendre.leggauss(24)
nphi = 48
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.repeat(wg[:,None], nphi, axis=1)*(2*np.pi/nphi)).ravel()
ct = ct.ravel(); ph = ph.ravel()
st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct
TH = np.arccos(ct)
ms = list(range(-2, 3))
Yd = {m: sph_harm(m, 2, ph, TH) for m in ms}
def proj_matrix(funcs):
    F = np.array(funcs).T
    Ginv = np.linalg.inv(F.conj().T @ (W[:,None]*F))
    B = np.array([Yd[m] for m in ms]).T
    PB = F @ (Ginv @ (F.conj().T @ (W[:,None]*B)))
    return B.conj().T @ (W[:,None]*PB)
Pt2g = proj_matrix([X*Y, X*Z, Y*Z])
Peg  = proj_matrix([X**2-Y**2, 3*Z**2-1.0+0j])
h1 = -4*Pt2g + 6*Peg
K = [0, 2, 4]
A = {k: np.zeros((5,5,5,5), dtype=complex) for k in K}
for k in K:
    Yk = {q: sph_harm(q, k, ph, TH) for q in range(-k,k+1)}
    for a,b,c,d in itertools.product(range(5), repeat=4):
        s = 0
        for q in range(-k,k+1):
            X1 = np.sum(W*np.conj(Yd[ms[a]])*Yd[ms[c]]*np.conj(Yk[q]))
            X2 = np.sum(W*np.conj(Yd[ms[b]])*Yd[ms[d]]*Yk[q])
            s += X1*X2
        A[k][a,b,c,d] = 4*np.pi/(2*k+1)*s
N = 10
def build_basis(nup, ndn):
    states = []
    for ou in itertools.combinations(range(5), nup):
        for od in itertools.combinations(range(5), ndn):
            s = 0
            for o in ou: s |= 1 << (2*o)
            for o in od: s |= 1 << (2*o+1)
            states.append(s)
    return states
def sgn(s, i): return (-1)**bin(s & ((1<<i)-1)).count('1')
def make_sector(nup, ndn):
    basis = build_basis(nup, ndn); idx = {s:i for i,s in enumerate(basis)}; D=len(basis)
    def op_1body(h):
        H = np.zeros((D,D))
        for j,s in enumerate(basis):
            for p in range(N):
                for q in range(N):
                    if p%2 != q%2: continue
                    hv = h[p//2, q//2]
                    if hv == 0 or not (s>>q)&1: continue
                    s1 = s ^ (1<<q); sg = sgn(s,q)
                    if (s1>>p)&1: continue
                    sg *= sgn(s1,p); s2 = s1 | (1<<p)
                    H[idx[s2], j] += sg*hv
        return H
    def op_2body(F):
        H = np.zeros((D,D))
        for j,s in enumerate(basis):
            # H = 1/2 sum V_abcd a†a a†b a_d a_c : apply a_c first, then a_d, then a†_b, then a†_a
            for c in range(N):
                if not (s>>c)&1: continue
                s1 = s ^ (1<<c); sg1 = sgn(s,c)
                for d in range(N):
                    if d==c or not (s1>>d)&1: continue
                    s2 = s1 ^ (1<<d); sg2 = sg1*sgn(s1,d)
                    for b in range(N):
                        if (s2>>b)&1: continue
                        s3 = s2 | (1<<b); sg3 = sg2*sgn(s2,b)
                        for a in range(N):
                            if (s3>>a)&1: continue
                            if a%2 != c%2 or b%2 != d%2: continue
                            v = sum(F[k]*A[k][a//2,b//2,c//2,d//2] for k in K).real
                            if abs(v) < 1e-14: continue
                            s4 = s3 | (1<<a); sg4 = sg3*sgn(s3,a)
                            H[idx[s4], j] += 0.5*sg4*v
        return H
    return basis, op_1body(h1), op_2body({0:0,2:1.0,4:0}), op_2body({0:0,2:0,4:1.0}), op_2body({0:1.0,2:0,4:0})
basis, H1, H2, H4, H0 = make_sector(4,1)
print("D =", len(basis))
print("symm:", np.allclose(H2,H2.T), np.allclose(H4,H4.T), np.allclose(H1,H1.T))
for name, M in [("F2",H2),("F4",H4)]:
    ev=np.linalg.eigvalsh(M); print(name, np.unique(np.round(ev-ev.min(),4), return_counts=True))
EOF