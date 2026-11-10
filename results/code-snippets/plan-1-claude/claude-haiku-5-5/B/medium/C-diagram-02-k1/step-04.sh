cat > ./ts_calc.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y

Cp = 3902/814            # C/B, with B = 1
F2 = 49.0 + 7.0*Cp        # Racah: F2 = 49B + 7C
F4 = 63.0*Cp/5.0          # F4 = 63C/5
Fk = {0: 0.0, 2: F2, 4: F4}

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
Ybasis = np.array([Ylm(2, m, pts) for m in ms])
def Drot(R):
    P2 = pts @ R
    Yr = np.array([Ylm(2, m, P2) for m in ms])
    return (np.conj(Ybasis) * W) @ Yr.T

C4 = np.array([[0,-1,0],[1,0,0],[0,0,1]], float)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]], float)
els = [np.eye(3)]
def known(R): return any(np.allclose(R, E) for E in els)
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
    if abs(t-3) < 1e-6: return 0
    if abs(t) < 1e-6: return 1
    if abs(t-1) < 1e-6: return 3
    return 2 if np.max(np.abs(R - np.diag(np.diag(R)))) < 0.5 else 4
classes = [cls(R) for R in els]
irr = {
 'A1': {0:1,1:1,2:1,3:1,4:1},
 'A2': {0:1,1:1,2:1,3:-1,4:-1},
 'E':  {0:2,1:-1,2:2,3:0,4:0},
 'T1': {0:3,1:0,2:-1,3:1,4:-1},
 'T2': {0:3,1:0,2:-1,3:-1,4:1},
}
irr_label = {'A1':'A1g','A2':'A2g','E':'Eg','T1':'T1g','T2':'T2g'}

nso = 10
def so(i, s): return 2*i + s
basis = list(itertools.combinations(range(nso), 4))
bidx = {b:i for i,b in enumerate(basis)}
N = len(basis)

def cdag(a, st):
    if a in st: return None, 0
    below = sum(1 for x in st if x < a)
    return tuple(sorted(st + (a,))), (-1)**below
def cann(a, st):
    if a not in st: return None, 0
    p = st.index(a)
    return tuple(x for x in st if x != a), (-1)**p

def one_body(h):
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

def spatial_to_so(hs):
    h = np.zeros((nso,nso), complex)
    for i in range(5):
        for j in range(5):
            for s in range(2):
                h[so(i,s), so(j,s)] = hs[i,j]
    return h

def gaunt_mat(k):
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
    for q in range(-k, k+1):
        A += (-1)**q * np.einsum('ac,bd->abcd', Gk[k][q], Gk[k][-q])
    return A
A_k = {k: ak(k) for k in (0,2,4)}
Vsp = sum(Fk[k]*A_k[k] for k in (0,2,4))
Vso = np.zeros((nso,nso,nso,nso), complex)
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

def vec(d):
    v = np.zeros(5, complex)
    for k,val in d.items(): v[ms.index(k)] = val
    return v
r2 = 1/np.sqrt(2)
eg_vecs = [vec({0:1}), vec({2:r2, -2:r2})]
t2g_vecs = [vec({1:r2, -1:r2}), vec({1:r2, -1:-r2}), vec({2:r2, -2:-r2})]
Peg = sum(np.outer(v, v.conj()) for v in eg_vecs)
Pt2g = sum(np.outer(v, v.conj()) for v in t2g_vecs)
hcf = -4*Pt2g + 6*Peg
Hcf = one_body(spatial_to_so(hcf))

Sz = np.zeros((N,N), complex); Sp = np.zeros((N,N), complex)
for i in range(5):
    hz = np.zeros((nso,nso), complex); hz[so(i,0),so(i,0)] = 0.5; hz[so(i,1),so(i,1)] = -0.5
    Sz += one_body(hz)
    hp = np.zeros((nso,nso), complex); hp[so(i,0), so(i,1)] = 1.0
    Sp += one_body(hp)
S2 = Sp.conj().T @ Sp + Sz @ Sz + Sz

def fock_rep(R):
    D = Drot(R)
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

print("Hee vs C4 commutator:", np.abs(Us[1] @ Hee - Hee @ Us[1]).max(), " Hcf:", np.abs(Us[1] @ Hcf - Hcf @ Us[1]).max())
print("[Hee,S2]:", np.abs(S2@Hee - Hee@S2).max(), " [Hee,C3]:", np.abs(Us[2] @ Hee - Hee @ Us[2]).max())

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
        mult = int(round(2*S+1))
        for name, tab in irr.items():
            n = sum(chi[g]*tab[classes[g]] for g in range(24))/24
            for _ in range(int(round(n.real))):
                out.append((E, f"{mult}{irr_label[name]}", j-i+1))
        i = j+1
    out.sort(key=lambda x: x[0])
    return out

if __name__ == "__main__":
    lv = levels(0.0)
    print("Dq=0 levels:", [(round(e,6), t, d) for e,t,d in lv])
    res = []
    for x in np.arange(0, 4.01, 0.5):
        L = levels(x)
        E0 = L[0][0]
        pts_ = [(round(e - E0, 6), t) for e, t, _ in L[:6]]
        print(f"Dq/B={x:.1f}:", pts_, " (n terms total:", len(L), ")")
        res.append((x, pts_))
    import json
    json.dump(res, open('ts_result.json','w'))
EOF
python3 ts_calc.py 2>&1 | grep -v -i matplotlib