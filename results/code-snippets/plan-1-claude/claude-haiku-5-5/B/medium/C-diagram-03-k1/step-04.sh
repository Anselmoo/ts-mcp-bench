cat > ts_d5.py << 'EOF'
import numpy as np, itertools, hashlib, os
from numpy.linalg import eigh

B = 806.0; C = 3570.0
F4 = 441*C/35.0
F2 = (441*B + 5*F4)/9.0
F = {0: 0.0, 2: F2, 4: F4}

def orbs(n):
    x, y, z = n[...,0], n[...,1], n[...,2]
    c = np.sqrt(15/(4*np.pi)); c2 = np.sqrt(15/(16*np.pi)); c3 = np.sqrt(5/(16*np.pi))
    return np.stack([c*x*y, c*y*z, c*x*z, c2*(x*x-y*y), c3*(3*z*z-1)], axis=-1)

xg, wg = np.polynomial.legendre.leggauss(20)
phis = np.arange(40)*2*np.pi/40
ct, ph = np.meshgrid(xg, phis, indexing='ij')
st = np.sqrt(1-ct**2)
pts = np.stack([st*np.cos(ph), st*np.sin(ph), ct], axis=-1).reshape(-1,3)
W = (np.repeat(wg[:,None], 40, axis=1)*(2*np.pi/40)).reshape(-1)
Phi = orbs(pts)
dots = pts @ pts.T
def Pk(k, t):
    if k == 0: return np.ones_like(t)
    if k == 2: return (3*t**2-1)/2
    if k == 4: return (35*t**4-30*t**2+3)/8
Fo = np.einsum('ia,ib->abi', Phi, Phi)
S0 = np.einsum('abi,i->ab', Fo, W)
assert np.allclose(S0, np.eye(5), atol=1e-10)
Iarr = np.zeros((5,5,5,5))
for k in (0,2,4):
    Pm = Pk(k, dots)
    T = np.einsum('acI,Ij->acj', Fo*W, Pm)
    A = np.einsum('acj,bdj->abcd', T*W, Fo)
    Iarr += F[k]*A

basis = list(itertools.combinations(range(10), 5))
index = {b: i for i, b in enumerate(basis)}
nb = len(basis)

def cann(state, p):
    if p not in state: return None
    return (-1)**sum(1 for q in state if q < p), tuple(q for q in state if q != p)
def cre(state, p):
    if p in state: return None
    return (-1)**sum(1 for q in state if q < p), tuple(sorted(state+(p,)))
def apply_chain(state, ops):
    sign = 1; s_ = state
    for typ, p in reversed(ops):
        r = cann(s_, p) if typ == 'a' else cre(s_, p)
        if r is None: return None
        s, s_ = r; sign *= s
    return sign, s_

H_ee = np.zeros((nb, nb))
orb_of = lambda p: p//2
spin_of = lambda p: p%2
for p, q, r, s in itertools.product(range(10), repeat=4):
    if spin_of(p) != spin_of(r) or spin_of(q) != spin_of(s): continue
    v = 0.5*Iarr[orb_of(p), orb_of(q), orb_of(r), orb_of(s)]
    if abs(v) < 1e-12: continue
    for i, s_ in enumerate(basis):
        res = apply_chain(s_, [('c',p),('c',q),('a',s),('a',r)])
        if res is None: continue
        sg, new = res
        H_ee[index[new], i] += sg*v
H_ee = 0.5*(H_ee+H_ee.T)
hcf = np.array([sum((-4.0 if orb_of(p) < 3 else 6.0) for p in s_) for s_ in basis])
Hcf = np.diag(hcf)

Sp = np.zeros((nb,nb))
for i, s_ in enumerate(basis):
    for o in range(5):
        res = apply_chain(s_, [('c',2*o),('a',2*o+1)])
        if res is None: continue
        sg, new = res
        Sp[index[new], i] += sg
Sm = Sp.T
Szd = np.array([0.5*sum(1 if p%2==0 else -1 for p in s_) for s_ in basis])
Sz = np.diag(Szd)
S2 = Sm@Sp + Sz@Sz + Sz

def rot_z(t): c,s=np.cos(t),np.sin(t); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
Cz4 = rot_z(np.pi/2)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]], float)
gens = [Cz4, C3]
G = [np.eye(3)]
def key(M): return tuple(np.round(M,6).ravel())
seen = {key(G[0])}
changed = True
while changed:
    changed = False
    for g in list(G):
        for h in gens:
            m = g@h
            if key(m) not in seen:
                seen.add(key(m)); G.append(m); changed = True
assert len(G) == 24, len(G)
def cls(M):
    tr = round(np.trace(M))
    if tr == 3: return 'E'
    if tr == 0: return 'C3'
    if tr == -1: return 'C2' if np.allclose(M, np.diag(np.diag(M))) else "C2'"
    if tr == 1: return 'C4'
classes = [cls(M) for M in G]
rng = np.random.default_rng(0)
samp = rng.normal(size=(60,3)); samp /= np.linalg.norm(samp,axis=1)[:,None]
Phis = orbs(samp)
JI = np.array(basis)
Gam = []
for M in G:
    Phir = orbs(samp @ np.linalg.inv(M).T)
    Mo, *_ = np.linalg.lstsq(Phis, Phir, rcond=None)
    assert np.allclose(Phis@Mo, Phir, atol=1e-10)
    Rs = np.kron(Mo, np.eye(2))
    sub = Rs[JI[:,None,:,None], JI[None,:,None,:]]
    Gam.append(np.linalg.det(sub))
Hfull = H_ee + 1000.0*Hcf
for Gm in Gam:
    assert np.allclose(Gm@Hfull, Hfull@Gm, atol=1e-6)
    assert np.allclose(Gm@S2, S2@Gm, atol=1e-8)
chartab = {
 'A1': {'E':1,'C3':1,'C2':1,'C4':1,"C2'":1},
 'A2': {'E':1,'C3':1,'C2':1,'C4':-1,"C2'":-1},
 'E':  {'E':2,'C3':-1,'C2':2,'C4':0,"C2'":0},
 'T1': {'E':3,'C3':0,'C2':-1,'C4':1,"C2'":-1},
 'T2': {'E':3,'C3':0,'C2':-1,'C4':-1,"C2'":1},
}
dims = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
w, v = eigh(S2)
Ssp = {}
for val in sorted(set(np.round(w,6))):
    Ssp[val] = v[:, np.abs(w-val)<1e-6]
blocks = []
for S2val, Vs in Ssp.items():
    Sfl = (-1+np.sqrt(1+4*S2val))/2
    mult = int(round(2*Sfl+1))
    PS = Vs@Vs.T
    for ir in dims:
        d = dims[ir]
        PG = np.zeros((nb,nb))
        for c, Gm in zip(classes, Gam):
            PG += chartab[ir][c]*Gm
        PG *= d/24.0
        P = PS@PG@PS
        P = 0.5*(P+P.T)
        ev, evec = eigh(P)
        Q = evec[:, ev > 0.5]
        if Q.shape[1] == 0: continue
        blocks.append((mult, ir, d, Q))
print("blocks (mult, irrep, #copies):", [(b[0],b[1],b[3].shape[1]//b[2]) for b in blocks])
print("Racah B,C check, F2,F4 =", F2, F4)

def levels_at(Dq):
    Hd = H_ee + Dq*Hcf
    out = []
    for mult, ir, d, Q in blocks:
        ev = np.sort(np.linalg.eigvalsh(Q.T@Hd@Q))
        groups = []
        for e in ev:
            if groups and abs(e-groups[-1][0]) < 1e-5: groups[-1][1] += 1
            else: groups.append([e, 1])
        for e, c in groups:
            assert c % d == 0, (ir, c, d)
            for _ in range(c//d):
                out.append((e, f"{mult}{ir}g"))
    out.sort()
    return out

results = {}
for dqb in np.arange(0, 4.01, 0.5):
    lv = levels_at(dqb*B)
    E0 = lv[0][0]
    top = [(lab, round((e-E0)/B, 4)) for e, lab in lv[:6]]
    results[round(float(dqb),2)] = top
    print(f"Dq/B={dqb:.1f}:", top)

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
dqs = np.linspace(0, 4.0, 81)
arrs = {}
for dqb in dqs:
    lv = levels_at(dqb*B)
    E0 = lv[0][0]
    byl = {}
    for e, lab in lv:
        byl.setdefault(lab, []).append((e-E0)/B)
    for lab, es in byl.items():
        arrs.setdefault(lab, []).append(sorted(es))
fig, ax = plt.subplots(figsize=(7,8))
for lab, rows in arrs.items():
    n = min(len(r) for r in rows)
    rows = np.array([r[:n] for r in rows])
    if rows.min() > 60: continue
    for j in range(n):
        ax.plot(dqs, rows[:, j], lw=1, color='k')
    ax.text(dqs[-1]+0.05, rows[-1,0], lab, fontsize=7, va='center')
ax.set_xlabel('Dq/B'); ax.set_ylabel('E/B')
ax.set_title('Tanabe-Sugano diagram d5 octahedral (B=806, C=3570 cm$^{-1}$)')
ax.set_xlim(0, 4.6); ax.set_ylim(0, 50)
fig.savefig('diagram.png', dpi=130)
print("saved", os.path.abspath('diagram.png'), hashlib.sha256(open('diagram.png','rb').read()).hexdigest())
EOF
time python3 ts_d5.py 2>&1 | grep -v -i matplotlib