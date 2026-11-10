mkdir -p /tmp/ts && cat > /tmp/ts/ts.py << 'EOF'
import numpy as np, itertools, math
from scipy.special import sph_harm_y
np.set_printoptions(precision=6, suppress=True)

B = 1.0
Cp = 3902/814
F2 = 49*B + 7*Cp
F4 = 63*Cp/5
Fk = {0: 0.0, 2: F2, 4: F4}

# quadrature grid on sphere
xg, wg = np.polynomial.legendre.leggauss(16)
nphi = 32
ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(np.arccos(xg), ph, indexing='ij')
W = np.outer(wg, np.full(nphi, 2*np.pi/nphi)).ravel()
pts = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)], -1).reshape(-1,3)
ms = [2,1,0,-1,-2]
def Ylm(l, m, P):
    th = np.arccos(np.clip(P[:,2], -1, 1)); phi = np.arctan2(P[:,1], P[:,0])
    return sph_harm_y(l, m, th, phi)

Ybasis = np.array([Ylm(2, m, pts) for m in ms])  # 5 x N
def Drot(R):
    # U f(n) = f(R^T n); D[m',m] = int Y_m'^* (n) Y_m(R^T n)
    P2 = pts @ R  # rows: (R^T n)^T = n^T R
    Yr = np.array([Ylm(2, m, P2) for m in ms])
    return (np.conj(Ybasis) * W) @ Yr.T

# group generation
C4 = np.array([[0,-1,0],[1,0,0],[0,0,1]], float)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]], float)
els = [np.eye(3)]
def known(R):
    return any(np.allclose(R, E) for E in els)
frontier = [np.eye(3)]
while frontier:
    new = []
    for A in frontier:
        for G in (C4, C3):
            P = A @ G
            if not known(P):
                els.append(P); new.append(P)
    frontier = new
assert len(els) == 24, len(els)

def cls(R):
    t = round(np.trace(R), 6)
    if abs(t-3) < 1e-6: return 0  # E
    if abs(t) < 1e-6: return 1    # C3
    if abs(t-1) < 1e-6: return 3  # C4
    # trace -1: C2 (z-type) or C2' (off-diagonal)
    return 2 if np.max(np.abs(R - np.diag(np.diag(R)))) < 0.5 else 4
classes = [cls(R) for R in els]
# class index map to 0..4 : E,C3,C2,C4,C2'
# Ordering in table: E, C3, C2(C4^2), C4, C2'
csize = {0:1,1:8,2:3,3:6,4:6}
irr = {
 'A1': {0:1,1:1,2:1,3:1,4:1},
 'A2': {0:1,1:1,2:1,3:-1,4:-1},
 'E':  {0:2,1:-1,2:2,3:0,4:0},
 'T1': {0:3,1:0,2:-1,3:1,4:-1},
 'T2': {0:3,1:0,2:-1,3:-1,4:1},
}
irr_label = {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}

# Fock space: 10 spin-orbitals: index = 2*i + s, i over ms, s=0 up, 1 down
nso = 10
def so(i, s): return 2*i + s
basis = list(itertools.combinations(range(nso), 4))
bidx = {b:i for i,b in enumerate(basis)}
N = len(basis)

def cdag(a, st):
    if a in st: return None, 0
    below = sum(1 for x in st if x < a)
    new = tuple(sorted(st + (a,)))
    return new, (-1)**below
def cann(a, st):
    if a not in st: return None, 0
    p = st.index(a)
    new = tuple(x for x in st if x != a)
    return new, (-1)**p

def op_apply_2(terms, st):
    """terms: list of (coef, a, b, d, c) meaning coef c†_a c†_b c_d c_c ; here generic"""
    pass

def one_body(h):  # h: nso x nso matrix, returns sum h_ab c†_a c_b
    M = np.zeros((N,N), complex)
    for j, st in enumerate(basis):
        for b in range(nso):
            s1, sg1 = cann(b, st)
            if s1 is None: continue
            for a in range(nso):
                if abs(h[a,b]) < 1e-14: continue
                s2, sg2 = cdag(a, s1)
                if s2 is None: continue
                M[bidx[s2], j] += h[a,b]*sg1*sg2
    return M

# spatial h
def spatial_to_so(hs):
    h = np.zeros((nso,nso), complex)
    for i in range(5):
        for j in range(5):
            for s in range(2):
                h[so(i,s), so(j,s)] = hs[i,j]
    return h

# Slater angular coefficients a_k(a,b,c,d) for spatial complex orbitals a..d (indices into ms)
def gaunt_mat(k):
    # G[q][a,c] = <a|C^k_q|c>
    out = {}
    for q in range(-k, k+1):
        Yk = Ylm(k, q, pts)
        M = np.array([[np.sum(np.conj(Ybasis[a])*Yk*Ybasis[c]*W) for c in range(5)] for a in range(5)])
        out[q] = np.sqrt(4*np.pi/(2*k+1)) * M
    return out
Gk = {k: gaunt_mat(k) for k in (2,4)}
Gk[0] = {0: np.ones((5,5), complex)}
def ak(k):
    A = np.zeros((5,5,5,5), complex)
    G = Gk[k]
    for q in range(-k, k+1):
        # sum_q (-1)^q <a|C^k_q|c><b|C^k_{-q}|d>
        A += (-1)**q * np.einsum('ac,bd->abcd', G[q], G[-q])
    return A
A_k = {k: ak(k) for k in (0,2,4)}

# two-body tensor in spin-orbital basis
Vso = np.zeros((nso,nso,nso,nso), complex)
Vsp = sum(Fk[k]*A_k[k] for k in (0,2,4))
for i,a,j,b in []: pass
for a in range(5):
    for b in range(5):
        for c in range(5):
            for d in range(5):
                v = Vsp[a,b,c,d]
                if abs(v) < 1e-14: continue
                for s1 in range(2):
                    for s2 in range(2):
                        Vso[so(a,s1), so(b,s2), so(c,s1), so(d,s2)] += v

def two_body(V):
    # H = 1/2 sum V_abcd c†_a c†_b c_d c_c
    M = np.zeros((N,N), complex)
    for j, st in enumerate(basis):
        for c in range(nso):
            s1, g1 = cann(c, st)
            if s1 is None: continue
            for d in range(nso):
                s2, g2 = cann(d, s1)
                if s2 is None: continue
                for b in range(nso):
                    s3, g3 = cdag(b, s2)
                    if s3 is None: continue
                    for a in range(nso):
                        v = V[a,b,c,d]
                        if abs(v) < 1e-14: continue
                        s4, g4 = cdag(a, s3)
                        if s4 is None: continue
                        M[bidx[s4], j] += 0.5*v*g1*g2*g3*g4
    return M

Hee = two_body(Vso)
# cubic field projectors (complex basis, m order 2,1,0,-1,-2)
e = np.eye(5)
def vec(d): 
    v = np.zeros(5, complex)
    for k,val in d.items(): v[ms.index(k)] = val
    return v
eg_vecs = [vec({0:1}), vec({2:1/np.sqrt(2), -2:1/np.sqrt(2)})]
t2g_vecs = [vec({1:1/np.sqrt(2), -1:1/np.sqrt(2)}) , vec({1:1/np.sqrt(2), -1:-1/np.sqrt(2)}), vec({2:1/np.sqrt(2), -2:-1/np.sqrt(2)})]
Peg = sum(np.outer(v, v.conj()) for v in eg_vecs)
Pt2g = sum(np.outer(v, v.conj()) for v in t2g_vecs)
hcf = -4*Pt2g + 6*Peg   # per Dq (units of Dq)
Hcf = one_body(spatial_to_so(hcf))

# spin operators
Sz = np.zeros((N,N), complex)
Sp = np.zeros((N,N), complex)
for i in range(5):
    hz = np.zeros((nso,nso), complex); hz[so(i,0),so(i,0)] = 0.5; hz[so(i,1),so(i,1)] = -0.5
    Sz += one_body(hz)
    hp = np.zeros((nso,nso), complex); hp[so(i,0), so(i,1)] = 1.0
    Sp += one_body(hp)
S2 = Sp.conj().T @ Sp + Sz @ Sz + Sz  # S- S+ = S^2 - Sz^2 - Sz  => S^2 = S-S+ + Sz^2 + Sz ; S- = Sp^dag
S2 = Sp.conj().T @ Sp + Sz @ Sz + Sz

# group rep on Fock space
def fock_rep(R):
    D = Drot(R)  # 5x5 complex, D[m',m]
    u = np.zeros((nso,nso), complex)
    for i in range(5):
        for j in range(5):
            for s in range(2):
                u[so(i,s), so(j,s)] = D[i,j]
    U = np.zeros((N,N), complex)
    for j, I in enumerate(basis):
        for i, J in enumerate(basis):
            U[i,j] = np.linalg.det(u[np.ix_(J, I)])
    return U
Us = [fock_rep(R) for R in els]

# check invariance
for U in Us[:3]:
    assert np.allclose(U.conj().T @ U, np.eye(N), atol=1e-8)
Hcheck = Hee + Hcf
print("commutator check (Hee with C4):", np.abs(Us[1] @ Hee - Hee @ Us[1]).max(), np.abs(Us[1] @ Hcf - Hcf @ Us[1]).max())
print("commutator with S2:", np.abs(S2@Hee - Hee@S2).max())

MU = 1000.0
def levels(Dq):
    H = Hee + Dq*Hcf + MU*S2
    H = (H + H.conj().T)/2
    w, V = np.linalg.eigh(H)
    out = []
    i = 0
    while i < N:
        j = i
        while j+1 < N and abs(w[j+1]-w[i]) < 1e-6: j += 1
        Wc = V[:, i:j+1]
        lam = w[i:j+1].mean()
        s2 = np.real(np.trace(Wc.conj().T @ S2 @ Wc))/Wc.shape[1]
        S = (-1 + np.sqrt(1+4*s2))/2
        E = lam - MU*s2
        chi = np.array([np.trace(Wc.conj().T @ U @ Wc) for U in Us])
        # decompose
        terms = []
        for name, tab in irr.items():
            n = sum(chi[g]*tab[classes[g]] for g in range(24))/24
            n = int(round(n.real))
            for _ in range(n):
                terms.append(irr_label[name])
        mult = int(round(2*S+1))
        for t in terms:
            out.append((E, f"{mult}{t}"))
        i = j+1
    out.sort(key=lambda x: x[0])
    return out

if __name__ == "__main__":
    import sys
    # sanity: total dims
    lv = levels(0.0)
    print("dim check (Dq=0):", len(lv))
    res = []
    for x in np.arange(0, 4.01, 0.5):
        L = levels(x*B)
        E0 = L[0][0]
        pts_ = [(round(e - E0, 6), t) for e, t in L[:6]]
        print(f"Dq/B={x:.1f}:", pts_)
        res.append((x, pts_))
    import pickle
    pickle.dump(res, open('/tmp/ts/res.pkl','wb'))
EOF
cd /tmp/ts && python3 ts.py 2>&1 | grep -v MPLCONFIG