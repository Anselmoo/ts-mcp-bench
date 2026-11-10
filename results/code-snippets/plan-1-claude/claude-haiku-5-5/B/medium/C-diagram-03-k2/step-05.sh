cd /tmp && python3 - << 'EOF'
import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
from collections import Counter

B = 806.0; Cc = 3570.0
Cb = Cc / B
F2 = 49.0 + 7.0*Cb
F4 = 12.6*Cb
assert abs((9*F2-5*F4)/441 - 1) < 1e-12 and abs(35*F4/441 - Cb) < 1e-12

nu, nphi = 20, 40
u, wu = leggauss(nu)
phi = np.arange(nphi)*2*np.pi/nphi
U, PH = np.meshgrid(u, phi, indexing='ij')
st = np.sqrt(1-U**2)
P = np.stack([(st*np.cos(PH)).ravel(), (st*np.sin(PH)).ravel(), U.ravel()], axis=1)
W = (np.outer(wu, np.full(nphi, 2*np.pi/nphi))).ravel()

def orbs(p):
    x, y, z = p[:,0], p[:,1], p[:,2]
    return np.stack([x*y, y*z, z*x, (x*x-y*y), (2*z*z-x*x-y*y)], axis=0)
F = orbs(P)
norms = np.sqrt((F**2 * W).sum(1))
F = F / norms[:,None]
G0 = (F*W) @ F.T
assert np.allclose(G0, np.eye(5), atol=1e-10)

cos_g = P @ P.T
Gk = {}
for k in (2, 4):
    Pk = eval_legendre(k, np.clip(cos_g, -1, 1))
    M = np.einsum('ap,cp->acp', F*W, F)
    N = np.einsum('bq,dq->bdq', F, F)
    Gk[k] = np.einsum('acp,pq,bdq->abcd', M, Pk*W[None,:], N, optimize=True)
Vint = F2*Gk[2] + F4*Gk[4]

NS = 10
states = list(itertools.combinations(range(NS), 5))
idx = {s: i for i, s in enumerate(states)}
D = len(states)

def apply_ops(ops, occ):
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
    M = np.zeros((D, D))
    for j, s in enumerate(states):
        for i in range(NS):
            for k in range(NS):
                if h[i, k] == 0: continue
                new, sg = apply_ops([('c', i), ('a', k)], s)
                if new is not None:
                    M[idx[new], j] += sg * h[i, k]
    return M

def op_matrix_2body(V):
    M = np.zeros((D, D))
    nz = np.argwhere(np.abs(V) > 1e-14)
    for (i, j, k, l) in nz:
        val = V[i, j, k, l]
        for jj, s in enumerate(states):
            new, sg = apply_ops([('c', i), ('c', j), ('a', l), ('a', k)], s)
            if new is not None:
                M[idx[new], jj] += 0.5 * sg * val
    return M

def so(orb, sp): return 2*orb + sp
Vso = np.zeros((NS,)*4)
for a, b, c, d in itertools.product(range(5), repeat=4):
    if abs(Vint[a,b,c,d]) < 1e-14: continue
    for s1 in range(2):
        for s2 in range(2):
            Vso[so(a,s1), so(b,s2), so(c,s1), so(d,s2)] = Vint[a,b,c,d]
H_ee = op_matrix_2body(Vso)

hcf = np.zeros((NS,NS))
for orb, val in zip(range(5), [-4,-4,-4,6,6]):
    for sp in range(2): hcf[so(orb,sp), so(orb,sp)] = val
H_cf = op_matrix_1body(hcf)

Sp1 = np.zeros((NS,NS))
for orb in range(5): Sp1[so(orb,0), so(orb,1)] = 1.0
Sp_m = op_matrix_1body(Sp1)
Sm_m = Sp_m.T
Szv = np.zeros((NS,NS))
for orb in range(5):
    Szv[so(orb,0), so(orb,0)] = 0.5; Szv[so(orb,1), so(orb,1)] = -0.5
Sz_m = op_matrix_1body(Szv)
S2 = Sm_m @ Sp_m + Sz_m @ (Sz_m + np.eye(D))

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
assert len(els) == 24

def classify(R):
    t = np.trace(R)
    if abs(t-3)<1e-9: return 'E'
    if abs(t)<1e-9: return 'C3'
    if abs(t-1)<1e-9: return 'C4'
    if abs(t+1)<1e-9:
        return 'C2' if np.allclose(R, np.diag(np.diag(R)), atol=1e-9) else "C2'"
    raise ValueError(t)
cls = [classify(R) for R in els]
print('classes:', Counter(cls))

rng = np.random.default_rng(0)
Q = rng.normal(size=(200,3)); Q /= np.linalg.norm(Q,axis=1)[:,None]
Fq = orbs(Q)/norms[:,None]
def Dmat(R):
    FR = orbs(Q @ R.T)/norms[:,None]
    return FR @ Fq.T @ np.linalg.inv(Fq @ Fq.T)
Ds = [Dmat(R) for R in els]
for Dm in Ds:
    assert np.allclose(Dm @ Dm.T, np.eye(5), atol=1e-8)

def gamma(Dm):
    U10 = np.kron(Dm, np.eye(2))
    M = np.zeros((D,D))
    for j, J in enumerate(states):
        for i, I in enumerate(states):
            M[j, i] = np.linalg.det(U10[np.ix_(J, I)])
    return M
Gam = [gamma(Dm) for Dm in Ds]

chi = {
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

def spectrum(Dq):
    H = H_ee + Dq*H_cf
    out = []
    for S in (2.5, 1.5, 0.5):
        PS = projector_S(S)
        for name in ('A1','A2','E','T1','T2'):
            M = projector_irrep(name) @ PS
            V = image_basis(M)
            if V.shape[1] == 0: continue
            Hs = V.T @ H @ V
            ev = np.sort(np.linalg.eigvalsh((Hs+Hs.T)/2))
            distinct = []
            for e in ev:
                if not distinct or abs(e-distinct[-1]) > 1e-6: distinct.append(e)
            for e in distinct:
                out.append((e, S, name, V.shape[1]//dims[name]))
    out.sort(key=lambda t: t[0])
    return out

# sanity: free-ion Dq=0 multiplet check
print('ranks', [image_basis(projector_irrep(n)@projector_S(2.5)).shape[1] for n in ('A1','T1','T2')])
for x in np.arange(0, 4.01, 0.5):
    sp = spectrum(x)
    e0 = sp[0][0]
    print(f"\nDq/B = {x:.1f}")
    for e, S, name, mult in sp[:9]:
        print(f"  {int(round(2*S+1))}{name}g  mult={mult}  E/B={(e-e0)/1.0:10.5f}")
EOF