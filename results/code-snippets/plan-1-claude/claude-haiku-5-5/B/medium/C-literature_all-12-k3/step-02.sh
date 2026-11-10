mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y, eval_legendre
from scipy.optimize import least_squares

# quadrature on sphere
x, wx = np.polynomial.legendre.leggauss(24)
nphi = 48
phis = np.arange(nphi)*2*np.pi/nphi
th = np.arccos(x)
TH, PH = np.meshgrid(th, phis, indexing='ij')
W = (np.outer(wx, np.ones(nphi))*2*np.pi/nphi).ravel()
TH = TH.ravel(); PH = PH.ravel()
n = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],1)
ms = [-2,-1,0,1,2]
Y = np.array([sph_harm_y(2, m, TH, PH) for m in ms])  # [m, p]
G = np.clip(n@n.T, -1, 1)
A = {}
for k in (0,2,4):
    P = eval_legendre(k, G)
    M1 = np.conj(Y)[:,None,:]*Y[None,:,:]*W[None,None,:]   # [m1,m3,p]
    M2 = np.conj(Y)[:,None,:]*Y[None,:,:]*W[None,None,:]   # [m2,m4,q]
    A[k] = np.einsum('abp,pq,cdq->abcd', M1, P, M2)
# real check: A0 should be delta
assert np.allclose(A[0], np.einsum('ab,cd->abcd', np.eye(5), np.eye(5)), atol=1e-8)

# spin-orbitals: index = 2*mi + s  (s=0 up, 1 down)
norb = 10
def sidx(mi, s): return 2*mi+s
# Coulomb two-electron matrix V[p,q,r,s] = <pq|V|rs> without F0
def Vmat(F2, F4):
    V = np.zeros((norb,)*4, dtype=complex)
    for a,b,c,d in itertools.product(range(5), repeat=4):
        ang = F2*A[2][a,c,b,d] + F4*A[4][a,c,b,d]
        for sa in (0,1):
            for sb in (0,1):
                V[sidx(a,sa), sidx(b,sb), sidx(c,sa), sidx(d,sb)] = ang
    return V
# one-electron ligand field in complex basis, Dq units
def hmat(Dq):
    Peg = np.zeros((5,5),complex); Pt = np.zeros((5,5),complex)
    Peg[2,2]=1
    e2 = np.zeros(5,complex); e2[0]=1/np.sqrt(2); e2[4]=1/np.sqrt(2)
    Peg += np.outer(e2,e2.conj())
    Pt[1,1]=1; Pt[3,3]=1
    t = np.zeros(5,complex); t[0]=1/np.sqrt(2); t[4]=-1/np.sqrt(2)
    Pt += np.outer(t,t.conj())
    h5 = 6*Dq*Peg - 4*Dq*Pt
    h = np.zeros((norb,norb),complex)
    for a in range(5):
        for b in range(5):
            for s in (0,1):
                h[sidx(a,s), sidx(b,s)] = h5[a,b]
    return h

# determinant basis, 7 electrons
dets = list(itertools.combinations(range(norb), 7))
index = {d:i for i,d in enumerate(dets)}
N = len(dets)

def apply_cdag_c(p, q, occ):
    """apply c+_p c_q to determinant occ (sorted tuple); return (sign, newocc) or None"""
    occ = list(occ)
    if q not in occ: return None
    sign = 1
    pos = occ.index(q)
    sign *= (-1)**pos
    occ.pop(pos)
    if p in occ: return None
    # insert p
    pos2 = sum(1 for x in occ if x < p)
    sign *= (-1)**pos2
    occ.insert(pos2, p)
    return sign, tuple(occ)

def build_H(Dq, B, C):
    F4 = 441*C/35; F2 = (441*B+5*F4)/9
    h = hmat(Dq); V = Vmat(F2, F4)
    H = np.zeros((N,N), complex)
    for j,d in enumerate(dets):
        for q in d:
            for p in range(norb):
                if abs(h[p,q])<1e-14: continue
                r = apply_cdag_c(p,q,d)
                if r is None: continue
                s,nd = r
                H[index[nd], j] += s*h[p,q]
        # two-body: 1/2 sum V[p,q,r,s] c+_p c+_q c_s c_r
        for r_ in d:
            for s_ in d:
                if r_==s_: continue
                # c_s c_r on d
                occ1 = list(d)
                # annihilate r then s
                res = apply_cdag_c_pure_annih(r_, occ1)
                if res is None: continue
                sg1, o1 = res
                res2 = apply_cdag_c_pure_annih(s_, list(o1))
                if res2 is None: continue
                sg2, o2 = res2
                for p in range(norb):
                    for q in range(norb):
                        if p==q or p in o2 or q in o2: continue
                        v = V[p,q,r_,s_]
                        if abs(v)<1e-14: continue
                        # create q then p: c+_p c+_q |o2>
                        o3 = list(o2)
                        sg = 1
                        if q in o3:
                            continue
                        pos = sum(1 for x in o3 if x<q); sg*=(-1)**pos
                        o3.insert(pos,q)
                        if p in o3: continue
                        pos = sum(1 for x in o3 if x<p); sg*=(-1)**pos
                        o3.insert(pos,p)
                        H[index[tuple(o3)], j] += 0.5*sg*sg2*sg1*v
    return H

def apply_cdag_c_pure_annih(q, occ):
    if q not in occ: return None
    pos = occ.index(q)
    sign = (-1)**pos
    occ2 = occ[:pos]+occ[pos+1:]
    return sign, tuple(occ2)

# S^2 operator via Sz and S+S-
def build_S2():
    # Sz
    Sz = np.zeros((N,N))
    for j,d in enumerate(dets):
        Sz[j,j] = 0.5*sum(1 if (x%2==0) else -1 for x in d)
    # S+ = sum_m c+_{m up} c_{m down}
    Sp = np.zeros((N,N))
    for j,d in enumerate(dets):
        for mi in range(5):
            r = apply_cdag_c_pure_annih(sidx(mi,1), list(d))  # annihilate down
            if r is None: continue
            sg, o = r
            if sidx(mi,0) in o: continue
            pos = sum(1 for x in o if x<sidx(mi,0))
            sg2 = (-1)**pos
            o2 = list(o); o2.insert(pos, sidx(mi,0))
            Sp[index[tuple(o2)], j] += sg*sg2
    Sm = Sp.T
    return Sz@Sz + 0.5*(Sp@Sm+Sm@Sp)

S2 = build_S2()

def levels(Dq, B, C):
    H = build_H(Dq,B,C).real
    H = 0.5*(H+H.T)
    w, v = np.linalg.eigh(H)
    s2 = np.einsum('ij,ik,kj->j', v, S2, v)
    out = {}
    quart = sorted([wi for wi,s in zip(w,s2) if abs(s-15/4)<1e-6])
    doub = sorted([wi for wi,s in zip(w,s2) if abs(s-3/4)<1e-6])
    return quart, doub
EOF
cd /w && python3 -c "
from ts import *
q,d = levels(1000,1000,4000)
print(len(q),len(d))
print(np.round(np.array(q)-q[0],1))
"