mkdir -p /work && cd /work && cat > ts.py << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre

B = 806.0; Cc = 3570.0
Cb = Cc / B                      # C/B in B units
F2 = 49.0 + 7.0*Cb               # Racah: F2 = 49B + 7C  (B=1 units)
F4 = 12.6*Cb                     # F4 = 441C/35
# check: B = (9F2-5F4)/441, C = 35F4/441
assert abs((9*F2-5*F4)/441 - 1) < 1e-12 and abs(35*F4/441 - Cb) < 1e-12

# quadrature on sphere
nu, nphi = 20, 40
u, wu = leggauss(nu)
phi = np.arange(nphi)*2*np.pi/nphi
U, PH = np.meshgrid(u, phi, indexing='ij')
st = np.sqrt(1-U**2)
P = np.stack([(st*np.cos(PH)).ravel(), (st*np.sin(PH)).ravel(), U.ravel()], axis=1)
W = (np.outer(wu, np.full(nphi, 2*np.pi/nphi))).ravel()

def orbs(p):
    x, y, z = p[:,0], p[:,1], p[:,2]
    return np.stack([x*y, y*z, z*x, (x*x-y*y), (2*z*z-x*x-y*y)], axis=0)  # 5 x n
F = orbs(P)
norms = np.sqrt((F**2 * W).sum(1))
F = F / norms[:,None]
# Gram-orthogonalize (x2-y2) vs (2z2-x2-y2): they are already orthogonal on sphere
G0 = (F*W) @ F.T
assert np.allclose(G0, np.eye(5), atol=1e-10), G0

cos_g = P @ P.T
Gk = {}
for k in (0, 2, 4):
    Pk = eval_legendre(k, np.clip(cos_g, -1, 1))
    M = np.einsum('ap,cp->acp', F*W, F)          # f_a f_c w
    N = np.einsum('bq,dq->bdq', F, F)            # f_b f_d
    Gk[k] = np.einsum('acp,pq,bdq->abcd', M, Pk*W[None,:], N, optimize=True)
Vd = {k: Gk[k] for k in Gk}
Vint = F0 = None
# Coulomb: V = F0*G0 + F2*G2 + F4*G4 with F0 = A + ... ; A (F0) does not affect relative levels; set F0=0
Vint = F2*Vd[2] + F4*Vd[4]

# spin-orbital index s = 2*orb + spin (spin 0 = up, 1 = down)
NS = 10
states = [c for c in itertools.combinations(range(NS), 5)]
idx = {s: i for i, s in enumerate(states)}
D = len(states)

def apply_ops(ops, occ):
    """ops: list of ('c'|'a', index) applied right-to-left (last in list acts first)."""
    occ = list(occ); sign = 1
    for typ, k in reversed(ops):
        n_below = sum(1 for o in occ if o < k)
        if typ == 'a':
            if k not in occ: return None, 0
            occ.remove(k); sign *= (-1)**n_below
        else:
            if k in occ: return None, 0
            occ.append(k); sign *= (-1)**n_below
            occ.sort()
    return tuple(occ), sign

def op_matrix_1body(h):
    M = np.zeros((D, D), dtype=complex)
    for j, s in enumerate(states):
        for i in range(NS):
            for k in range(NS):
                if h[i, k] == 0: continue
                new, sg = apply_ops([('c', i), ('a', k)], s)
                if new is not None:
                    M[idx[new], j] += sg * h[i, k]
    return M

def op_matrix_2body(V):
    M = np.zeros((D, D), dtype=complex)
    nz = np.argwhere(np.abs(V) > 1e-14)
    for (i, j, k, l) in nz:
        val = V[i, j, k, l]
        for jj, s in enumerate(states):
            new, sg = apply_ops([('c', i), ('c', j), ('a', l), ('a', k)], s)
            if new is not None:
                M[idx[new], jj] += 0.5 * sg * val
    return M

# spin-orbital two-body
def so_index(orb, sp): return 2*orb + sp
Vso = np.zeros((NS,)*4)
for a in range(5):
  for b in range(5):
    for c in range(5):
      for d in range(5):
        if abs(Vint[a,b,c,d]) < 1e-14: continue
        for s1 in range(2):
          for s2 in range(2):
            Vso[so_index(a,s1), so_index(b,s2), so_index(c,s1), so_index(d,s2)] = Vint[a,b,c,d]
H_ee = op_matrix_2body(Vso)

# crystal field unit (per Dq): t2g (0,1,2): -4 ; eg (3,4): +6
hcf = np.zeros((NS,NS))
for orb, val in zip(range(5), [-4,-4,-4,6,6]):
    for sp in range(2): hcf[so_index(orb,sp), so_index(orb,sp)] = val
H_cf = op_matrix_1body(hcf)

# spin operators
Splus_1 = np.zeros((NS,NS))
for orb in range(5): Splus_1[so_index(orb,0), so_index(orb,1)] = 1.0
Sp = op_matrix_1body(Splus_1)
Sm = Sp.conj().T
Szv = np.zeros((NS,NS))
for orb in range(5):
    Szv[so_index(orb,0), so_index(orb,0)] = 0.5; Szv[so_index(orb,1), so_index(orb,1)] = -0.5
Sz = op_matrix_1body(Szv)
S2 = Sm @ Sp + Sz @ (Sz + np.eye(D))

# group elements: generate O from C4z and C3(111)
def rot(axis, ang):
    axis = np.array(axis, float); axis /= np.linalg.norm(axis)
    K = np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
    return np.eye(3) + np.sin(ang)*K + (1-np.cos(ang))*K@K
gens = [rot([0,0,1], np.pi/2), rot([1,1,1], 2*np.pi/3)]
els = [np.eye(3)]
changed = True
while changed:
    changed = False
    for g in list(els):
        for h in gens:
            n = h @ g
            if not any(np.allclose(n, e, atol=1e-9) for e in els):
                els.append(n); changed = True
assert len(els) == 24, len(els)

def classify(R):
    t = np.trace(R)
    if np.allclose(R, np.eye(3)): return 'E'
    if abs(t-3)<1e-9: return 'E'
    if abs(t)<1e-9: return 'C3'
    if abs(t-1)<1e-9: return 'C4'
    if abs(t+1)<1e-9:
        return 'C2' if np.allclose(R, np.diag(np.diag(R)), atol=1e-9) else "C2'"
    raise ValueError
cls = [classify(R) for R in els]
from collections import Counter
print(Counter(cls))

# D(R) on orbitals: f_a(R q) = sum_b D_ab f_b(q)
rng = np.random.default_rng(0)
Q = rng.normal(size=(200,3)); Q /= np.linalg.norm(Q,axis=1)[:,None]
Fq = orbs(Q); Fq = Fq/norms[:,None]
def Dmat(R):
    FR = orbs(Q @ R.T); FR = FR/norms[:,None]   # rows: R q
    return FR @ Fq.T @ np.linalg.inv(Fq @ Fq.T)
Ds = [Dmat(R) for R in els]
for R, Dm in zip(els, Ds):   # sanity: orthogonal
    assert np.allclose(Dm @ Dm.T, np.eye(5), atol=1e-8)

def gamma(Dm):
    U10 = np.kron(Dm, np.eye(2))  # spin-orbital index 2*orb+spin
    M = np.zeros((D,D))
    for j, J in enumerate(states):
        for i, I in enumerate(states):
            M[j, i] = np.linalg.det(U10[np.ix_(J, I)])
    return M
Gam = [gamma(Dm) for Dm in Ds]

chi = {  # classes: E, C3, C2, C4, C2'
 'A1':{'E':1,'C3':1,'C2':1,'C4':1,"C2'":1},
 'A2':{'E':1,'C3':1,'C2':1,'C4':-1,"C2'":-1},
 'E': {'E':2,'C3':-1,'C2':2,'C4':0,"C2'":0},
 'T1':{'E':3,'C3':0,'C2':-1,'C4':1,"C2'":-1},
 'T2':{'E':3,'C3':0,'C2':-1,'C4':-1,"C2'":1}}
dims = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}

def projector_irrep(name):
    P_ = np.zeros((D,D))
    for c, G in zip(cls, Gam):
        P_ += chi[name][c] * G
    return P_ * dims[name] / 24.0

Sc = {2.5: 2.5*3.5, 1.5: 1.5*2.5, 0.5: 0.5*1.5}
def projector_S(S):
    P_ = np.eye(D)
    for Sp_ in Sc:
        if Sp_ != S:
            P_ = P_ @ (S2 - Sc[Sp_]*np.eye(D)) / (Sc[S]-Sc[Sp_])
    return P_

def image_basis(M):
    u_, s_, vh = np.linalg.svd(M)
    return u_[:, s_ > 0.5]

levels = []  # (S, irrep, energy_unit_Dq-dependent) computed per Dq
def spectrum(Dq):
    H = H_ee + Dq*H_cf
    out = []
    for S in (2.5, 1.5, 0.5):
        PS = projector_S(S)
        for name in ('A1','A2','E','T1','T2'):
            PG = projector_irrep(name)
            M = PG @ PS
            if np.linalg.norm(M) < 1e-8: continue
            V = image_basis(M)
            if V.shape[1] == 0: continue
            Hs = V.conj().T @ H @ V
            ev = np.sort(np.linalg.eigvalsh((Hs+Hs.conj().T)/2))
            # distinct
            distinct = []
            for e in ev:
                if not distinct or abs(e-distinct[-1]) > 1e-6: distinct.append(e)
            for e in distinct:
                out.append((e, S, name))
    out.sort(key=lambda t: t[0])
    return out

if __name__ == '__main__':
    import sys, json
    res = {}
    for x in np.arange(0, 4.01, 0.5):
        sp = spectrum(x)
        e0 = sp[0][0]
        print(f"\nDq/B = {x:.1f}  (levels: {len(sp)})")
        for e, S, name in sp[:10]:
            print(f"  {int(round(2*S+1))}{name}g   {e-e0:10.5f}")
EOF
time python3 ts.py