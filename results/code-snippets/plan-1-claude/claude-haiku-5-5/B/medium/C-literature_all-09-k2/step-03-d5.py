import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares

# angular grid (exact for polynomial degree <= ~30)
xg, wg = np.polynomial.legendre.leggauss(24)
nphi = 48
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.repeat(wg[:,None], nphi, axis=1)*(2*np.pi/nphi)).ravel()
ct = ct.ravel(); ph = ph.ravel()
st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct

def Ylm(l, m):
    # scipy sph_harm(m, l, azimuth, polar)
    return sph_harm(m, l, ph, np.arccos(ct))

# d orbital basis m=-2..2
Yd = {m: Ylm(2, m) for m in range(-2, 3)}
ms = list(range(-2, 3))
# cubic angular functions (unnormalised)
cub = {
 't2g': [X*Y, X*Z, Y*Z],
 'eg':  [X**2-Y**2, 3*Z**2-1.0],
}
def proj_matrix(funcs):
    # projector (in Y_m basis, 5x5) onto span of funcs, L2 on sphere
    F = np.array(funcs).T           # grid x n
    G = F.conj().T @ (W[:,None]*F)
    Ginv = np.linalg.inv(G)
    # matrix elements <Y_m| P |Y_m'> = sum_grid W conj(Y_m) (P Y_m')
    B = np.array([Yd[m] for m in ms]).T   # grid x 5
    PB = F @ (Ginv @ (F.conj().T @ (W[:,None]*B)))
    return B.conj().T @ (W[:,None]*PB)
Pt2g = proj_matrix(cub['t2g'])
Peg  = proj_matrix(cub['eg'])
# octahedral one-electron matrix per unit Dq: t2g -4Dq, eg +6Dq
h1 = -4*Pt2g + 6*Peg
print("trace check (should be ~0):", np.trace(h1).real)
print("h1 Hermitian:", np.allclose(h1, h1.conj().T))

# two-electron angular coefficients a_k(a,b,c,d) with Slater F^k
def angular(a, b, c, d, k):
    # <ab|1/r12|cd> = sum_k F^k * (4pi/(2k+1)) * sum_q X1*X2
    s = 0
    for q in range(-k, k+1):
        if abs(q) > 2*0+k: continue
        Ykq = sph_harm(q, k, ph, np.arccos(ct))
        X1 = np.sum(W*np.conj(Yd[ms[a]])*Yd[ms[c]]*np.conj(Ykq))
        X2 = np.sum(W*np.conj(Yd[ms[b]])*Yd[ms[d]]*Ykq)
        s += X1*X2
    return 4*np.pi/(2*k+1)*s
K = [0, 2, 4]
A = {k: np.zeros((5,5,5,5), dtype=complex) for k in K}
for a,b,c,d in itertools.product(range(5), repeat=4):
    for k in K:
        A[k][a,b,c,d] = angular(a,b,c,d,k)

# spin orbitals: index = 2*orb + spin (spin 0=up,1=down)
N = 10
def build_basis(nup, ndn):
    states = []
    for occ_up in itertools.combinations(range(5), nup):
        for occ_dn in itertools.combinations(range(5), ndn):
            s = 0
            for o in occ_up: s |= 1 << (2*o)
            for o in occ_dn: s |= 1 << (2*o+1)
            states.append(s)
    return states
basis = build_basis(4, 1)
idx = {s:i for i,s in enumerate(basis)}
D = len(basis)

def apply_cdag_c(p, q, s):
    # a_p^dagger a_q on bitstring s; returns (sign, newstate) or None
    if not (s >> q) & 1: return None
    sign = (-1)**bin(s & ((1<<q)-1)).count('1')
    s2 = s ^ (1<<q)
    if (s2 >> p) & 1: return None
    sign *= (-1)**bin(s2 & ((1<<p)-1)).count('1')
    return sign, s2 | (1<<p)

def op_matrices(Vint, h):
    # returns D x D matrix of one-body h (spin-diagonal) + two-body with integrals Vint(a,b,c,d) on spin orbitals
    H = np.zeros((D,D), dtype=complex)
    for j,s in enumerate(basis):
        # one-body
        for p in range(N):
            for q in range(N):
                if p%2 != q%2: continue
                hv = h[p//2, q//2]
                if abs(hv) < 1e-14: continue
                r = apply_cdag_c(p, q, s)
                if r is None: continue
                sg, s2 = r
                H[idx[s2], j] += sg*hv
        # two-body: 1/2 sum V_abcd a†_a a†_b a_d a_c
        for c_ in range(N):
            for d_ in range(N):
                if not (s>>c_)&1 or not (s>>d_)&1 and c_!=d_: pass
                # apply a_d then a_c
                if not (s>>d_)&1: continue
                s1 = s ^ (1<<d_); sg1 = (-1)**bin(s & ((1<<d_)-1)).count('1')
                if not (s1>>c_)&1: continue
                sg2 = (-1)**bin(s1 & ((1<<c_)-1)).count('1')
                s2 = s1 ^ (1<<c_); sgt = sg1*sg2
                for a_ in range(N):
                    for b_ in range(N):
                        v = Vint(a_, b_, c_, d_)
                        if v == 0: continue
                        if (s2>>b_)&1: continue
                        sb = (-1)**bin(s2 & ((1<<b_)-1)).count('1')
                        s3 = s2 | (1<<b_)
                        if (s3>>a_)&1: continue
                        sa = (-1)**bin(s3 & ((1<<a_)-1)).count('1')
                        s4 = s3 | (1<<a_)
                        H[idx[s4], j] += 0.5*sgt*sb*sa*v
    return H

def Vfun(F):
    def V(a,b,c,d):
        # spin-orbital indices
        if a%2 != c%2 or b%2 != d%2: return 0
        ao, bo, co, do = a//2, b//2, c//2, d//2
        return sum(F[k]*A[k][ao,bo,co,do] for k in K)
    return V

# one-body crystal field in spin-orbital form uses h[orb,orb]
def H_of(Dq, F0, F2, F4):
    h = Dq*h1
    # two-body
    Hee = op_matrices(Vfun({0:F0,2:F2,4:F4}), np.zeros((5,5)))
    Hcf = op_matrices(lambda a,b,c,d: 0, h)
    return Hcf + Hee
