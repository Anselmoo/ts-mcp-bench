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
def Ylm(l, m): return sph_harm(m, l, ph, TH)
ms = list(range(-2, 3))
Yd = {m: Ylm(2, m) for m in ms}

def proj_matrix(funcs):
    F = np.array(funcs).T
    G = F.conj().T @ (W[:,None]*F)
    Ginv = np.linalg.inv(G)
    B = np.array([Yd[m] for m in ms]).T
    PB = F @ (Ginv @ (F.conj().T @ (W[:,None]*B)))
    return B.conj().T @ (W[:,None]*PB)
Pt2g = proj_matrix([X*Y, X*Z, Y*Z])
Peg  = proj_matrix([X**2-Y**2, 3*Z**2-1.0+0j])
h1 = -4*Pt2g + 6*Peg
print("trace:", np.trace(h1).real, "herm:", np.allclose(h1, h1.conj().T))

K = [0, 2, 4]
A = {k: np.zeros((5,5,5,5), dtype=complex) for k in K}
Ykq_cache = {(k,q): sph_harm(q, k, ph, TH) for k in K for q in range(-k,k+1)}
for a,b,c,d in itertools.product(range(5), repeat=4):
    for k in K:
        s = 0
        for q in range(-k, k+1):
            Ykq = Ykq_cache[(k,q)]
            X1 = np.sum(W*np.conj(Yd[ms[a]])*Yd[ms[c]]*np.conj(Ykq))
            X2 = np.sum(W*np.conj(Yd[ms[b]])*Yd[ms[d]]*Ykq)
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
basis = build_basis(4, 1)
idx = {s:i for i,s in enumerate(basis)}
D = len(basis)

def sgn(s, i): return (-1)**bin(s & ((1<<i)-1)).count('1')

def op_1body(h):
    H = np.zeros((D,D), dtype=complex)
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
    H = np.zeros((D,D), dtype=complex)
    for j,s in enumerate(basis):
        for c in range(N):
            for d in range(N):
                if not (s>>d)&1: continue
                s1 = s ^ (1<<d); sg1 = sgn(s,d)
                if not (s1>>c)&1: continue
                s2 = s1 ^ (1<<c); sg2 = sg1*sgn(s1,c)
                for a in range(N):
                    for b in range(N):
                        if a%2 != c%2 or b%2 != d%2: continue
                        v = sum(F[k]*A[k][a//2,b//2,c//2,d//2] for k in K)
                        if abs(v) < 1e-14: continue
                        if (s2>>b)&1: continue
                        sb = sgn(s2,b); s3 = s2 | (1<<b)
                        if (s3>>a)&1: continue
                        sa = sgn(s3,a); s4 = s3 | (1<<a)
                        H[idx[s4], j] += 0.5*sg2*sb*sa*v
    return H

H1 = op_1body(h1).real
H2 = op_2body({0:0.0, 2:1.0, 4:0.0}).real
H4 = op_2body({0:0.0, 2:0.0, 4:1.0}).real
print("symmetric:", np.allclose(H2,H2.T), np.allclose(H4,H4.T), np.allclose(H1,H1.T))

def spectrum(Dq, B, C):
    F2 = 49*B + 7*C
    F4 = 63*C/5
    return np.linalg.eigvalsh(Dq*H1 + F2*H2 + F4*H4)

ev = spectrum(0.0, 1.0, 0.0)
vals = np.round(ev - ev.min(), 6)
u, cnt = np.unique(vals, return_counts=True)
print("free ion, B=1, C=0:")
for x,c in zip(u,cnt): print(f"{x:10.4f}  x{c}")
ev = spectrum(0.0, 0.0, 1.0)
vals = np.round(ev - ev.min(), 6)
u, cnt = np.unique(vals, return_counts=True)
print("free ion, C=1, B=0:")
for x,c in zip(u,cnt): print(f"{x:10.4f}  x{c}")
