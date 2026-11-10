cat > ts.py << 'EOF'
import numpy as np, itertools, sys
from sympy.physics.wigner import wigner_3j
from scipy.linalg import expm
from collections import Counter

B = 1.0
C = 2511/551
F2 = 49*B + 7*C
F4 = 12.6*C
Fk = {0: 0.0, 2: F2, 4: F4}   # F0 omitted (constant for fixed n)

NE = int(sys.argv[1]) if len(sys.argv) > 1 else 6
l = 2
ms = list(range(-2, 3))
nso = 10
spin_of = [i % 2 for i in range(nso)]
orb_of = [i//2 for i in range(nso)]

def angular(k, q, ma, mc):
    m_a = ms[ma]; m_c = ms[mc]
    if q != m_a - m_c or abs(q) > k: return 0.0
    phase = (-1)**(abs(m_a))
    w1 = float(wigner_3j(l, k, l, -m_a, q, m_c))
    w0 = float(wigner_3j(l, k, l, 0, 0, 0))
    return phase * (2*l+1) * w1 * w0

def eri_spatial(ma, mb, mc, md):
    tot = 0.0
    for k in (0, 2, 4):
        if Fk[k] == 0: continue
        for q in range(-k, k+1):
            a1 = angular(k, q, ma, mc)
            if a1 == 0: continue
            a2 = angular(k, -q, mb, md)
            if a2 == 0: continue
            tot += Fk[k] * (-1)**(q % 2) * a1 * a2
    return tot

V = np.zeros((nso,)*4)
for a, b, c, d in itertools.product(range(nso), repeat=4):
    if spin_of[a] != spin_of[c] or spin_of[b] != spin_of[d]: continue
    V[a, b, c, d] = eri_spatial(orb_of[a], orb_of[b], orb_of[c], orb_of[d])

basis = [sum(1 << i for i in occ) for occ in itertools.combinations(range(nso), NE)]
index = {s: i for i, s in enumerate(basis)}
dim = len(basis)

def annih(i, state):
    if not (state >> i) & 1: return None, 0
    return state ^ (1 << i), (-1)**bin(state & ((1 << i) - 1)).count('1')
def create(i, state):
    if (state >> i) & 1: return None, 0
    return state | (1 << i), (-1)**bin(state & ((1 << i) - 1)).count('1')

def two_body_matrix(Vt):
    M = np.zeros((dim, dim))
    nz = list(zip(*np.nonzero(np.abs(Vt) > 1e-14)))
    for j, s in enumerate(basis):
        for a, b, c, d in nz:
            s1, sg1 = annih(c, s)
            if sg1 == 0: continue
            s2, sg2 = annih(d, s1)
            if sg2 == 0: continue
            s3, sg3 = create(b, s2)
            if sg3 == 0: continue
            s4, sg4 = create(a, s3)
            if sg4 == 0: continue
            M[index[s4], j] += 0.5 * Vt[a, b, c, d] * sg1*sg2*sg3*sg4
    return M

def one_body_matrix(h):
    M = np.zeros((dim, dim))
    for j, s in enumerate(basis):
        for a in range(nso):
            for c in range(nso):
                if abs(h[a, c]) < 1e-14: continue
                s1, sg1 = annih(c, s)
                if sg1 == 0: continue
                s2, sg2 = create(a, s1)
                if sg2 == 0: continue
                M[index[s2], j] += h[a, c] * sg1 * sg2
    return M

Hee = two_body_matrix(V)

# octahedral one-electron field: eg = {d_z2, d_x2-y2} -> +6Dq, t2g -> -4Dq
Peg = np.zeros((5, 5), complex)
Peg[2, 2] = 1.0
v = np.zeros(5, complex); v[0] = 1/np.sqrt(2); v[4] = 1/np.sqrt(2)
Peg += np.outer(v, v.conj())
Pt2 = np.eye(5) - Peg
h_orb = 6*Peg - 4*Pt2
h_so = np.kron(h_orb, np.eye(2))
Hcf = one_body_matrix(h_so)

Sp = np.zeros((nso, nso)); Sz = np.zeros((nso, nso))
for mi in range(5):
    Sp[2*mi, 2*mi+1] = 1.0
    Sz[2*mi, 2*mi] = 0.5; Sz[2*mi+1, 2*mi+1] = -0.5
Spm = one_body_matrix(Sp); Szm = one_body_matrix(Sz)
S2 = Spm.T @ Spm + Szm @ Szm + Szm

Lz = np.diag(ms).astype(complex)
Lp = np.zeros((5, 5), complex)
for i, m in enumerate(ms[:-1]):
    Lp[i+1, i] = np.sqrt(l*(l+1) - m*(m+1))
Lm = Lp.conj().T
Lx = (Lp + Lm)/2; Ly = (Lp - Lm)/(2j)
def Urot(axis, theta):
    n = np.array(axis, float); n /= np.linalg.norm(n)
    return expm(-1j*theta*(n[0]*Lx + n[1]*Ly + n[2]*Lz))
def Rrot(axis, theta):
    n = np.array(axis, float); n /= np.linalg.norm(n)
    K = np.array([[0,-n[2],n[1]],[n[2],0,-n[0]],[-n[1],n[0],0]])
    return np.eye(3) + np.sin(theta)*K + (1-np.cos(theta))*K@K
gens = [(Rrot([0,0,1], np.pi/2), Urot([0,0,1], np.pi/2)),
        (Rrot([1,1,1], 2*np.pi/3), Urot([1,1,1], 2*np.pi/3))]
grp = [(np.eye(3), np.eye(5, dtype=complex))]
key = lambda R: tuple(np.round(R, 6).flatten())
seen = {key(grp[0][0])}
frontier = list(grp)
while frontier:
    new = []
    for R, U in frontier:
        for Rg, Ug in gens:
            R2 = Rg @ R; U2 = Ug @ U
            k = key(R2)
            if k not in seen:
                seen.add(k); grp.append((R2, U2)); new.append((R2, U2))
    frontier = new
assert len(grp) == 24, len(grp)

def classify(R):
    tr = np.trace(R)
    if abs(tr-3) < 1e-6: return 'E'
    if abs(tr) < 1e-6: return 'C3'
    if abs(tr-1) < 1e-6: return 'C4'
    w, vec = np.linalg.eig(R)
    n = np.real(vec[:, np.argmin(np.abs(w-1))])
    return 'C2f' if np.sum(np.abs(n) > 1e-6) == 1 else 'C2e'
cls = [classify(R) for R, _ in grp]
irr = {
 'A1': {'E':1,'C3':1,'C2f':1,'C4':1,'C2e':1},
 'A2': {'E':1,'C3':1,'C2f':1,'C4':-1,'C2e':-1},
 'E':  {'E':2,'C3':-1,'C2f':2,'C4':0,'C2e':0},
 'T1': {'E':3,'C3':0,'C2f':-1,'C4':1,'C2e':-1},
 'T2': {'E':3,'C3':0,'C2f':-1,'C4':-1,'C2e':1},
}

def many_body(U5):
    U10 = np.kron(U5, np.eye(2))
    M = np.zeros((dim, dim), complex)
    for j, sj in enumerate(basis):
        occ_j = [i for i in range(nso) if (sj >> i) & 1]
        for i, si in enumerate(basis):
            occ_i = [k for k in range(nso) if (si >> k) & 1]
            M[i, j] = np.linalg.det(U10[np.ix_(occ_i, occ_j)])
    return M
Gam = [many_body(U) for _, U in grp]

def analyze(Dq):
    H = Hee + Dq*Hcf
    w, Vv = np.linalg.eigh(H + 1000.0*S2)
    levels = []
    i = 0
    while i < dim:
        j = i
        while j+1 < dim and abs(w[j+1]-w[i]) < 1e-6: j += 1
        block = Vv[:, i:j+1]
        eb, ub = np.linalg.eigh(block.conj().T @ H @ block)
        k = 0
        while k < len(eb):
            kk = k
            while kk+1 < len(eb) and abs(eb[kk+1]-eb[k]) < 1e-6: kk += 1
            Vsub = block @ ub[:, k:kk+1]
            P = Vsub @ Vsub.conj().T
            dimsub = kk-k+1
            S2val = np.real(np.trace(P @ S2)) / dimsub
            S = (-1 + np.sqrt(1 + 4*S2val))/2
            chars = [np.trace(P @ Gam[g]) for g in range(24)]
            for name, tab in irr.items():
                mult = sum(chars[g]*tab[cls[g]] for g in range(24))/24
                for _ in range(int(round(mult.real))):
                    levels.append((float(np.mean(eb[k:kk+1])), S, name))
            k = kk+1
        i = j+1
    levels.sort(key=lambda x: x[0])
    return levels
EOF
cat > run_test.py << 'EOF'
import sys
sys.argv = ['x', '2']
exec(open('ts.py').read())
lv = analyze(0.0)
for e, S, nm in lv: print(round(e, 5), S, nm)
EOF
python3 run_test.py