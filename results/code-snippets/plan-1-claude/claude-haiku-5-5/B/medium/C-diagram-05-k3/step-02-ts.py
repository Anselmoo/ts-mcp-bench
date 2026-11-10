import itertools, numpy as np
from numpy.linalg import det
from scipy.special import sph_harm_y

B = 1.0
C = 3660/859
F4 = 441*C/35
F2 = (441*B + 5*F4)/9
Fk = {0: 0.0, 2: F2, 4: F4}

# ---- real d orbitals as polynomials (order: z2, x2-y2, xy, xz, yz)
polys = [lambda x,y,z: 2*z*z-x*x-y*y,
         lambda x,y,z: x*x-y*y,
         lambda x,y,z: x*y,
         lambda x,y,z: x*z,
         lambda x,y,z: y*z]
def sph_pts(nth=24, nph=48):
    xg, wg = np.polynomial.legendre.leggauss(nth)
    ph = np.arange(nph)*2*np.pi/nph
    pts, w = [], []
    for ct, wt in zip(xg, wg):
        st = np.sqrt(1-ct*ct)
        for p in ph:
            pts.append([st*np.cos(p), st*np.sin(p), ct]); w.append(wt*2*np.pi/nph)
    return np.array(pts), np.array(w)
P, W = sph_pts()
X, Y, Z = P.T
raw = np.array([f(X,Y,Z) for f in polys]).T  # npts x 5
norms = np.sqrt((raw**2 * W[:,None]).sum(0))
def psi(pts):
    x,y,z = pts.T
    return np.array([f(x,y,z) for f in polys]).T / norms
# check orthonormality
G = (psi(P)*W[:,None]).T @ psi(P)
assert np.allclose(G, np.eye(5), atol=1e-10), G

# ---- Coulomb angular coefficients a^k(a,b,c,d) in real basis
Psi = psi(P)
ang = {}
for k in (2,4):
    for q in range(-k,k+1):
        Ykq = sph_harm_y(k, abs(q), np.arccos(np.clip(Z,-1,1)), np.arctan2(Y,X))  # placeholder, fixed below
for k in (0,2,4):
    # A[a,c,q] = int psi_a Y_kq^* psi_c
    qs = list(range(-k,k+1))
    A = np.zeros((5,5,len(qs)),dtype=complex)
    th = np.arccos(np.clip(Z,-1,1)); ph = np.arctan2(Y,X)
    for iq,q in enumerate(qs):
        Yk = sph_harm_y(k, q, th, ph)
        A[:,:,iq] = np.einsum('pa,p,pc->ac', Psi, W*np.conj(Yk), Psi)
    ang[k] = (qs, A)
def ak(k,a,b,c,d):
    qs, A = ang[k]
    s = 0
    for iq,q in enumerate(qs):
        # sum_q (4pi/(2k+1)) [int psi_a Y^*_kq psi_c][int psi_b Y_kq psi_d]
        # second factor = int psi_b Y_kq psi_d = conj(int psi_b Y_kq^* psi_d) for real psi
        s += A[a,c,iq] * np.conj(A[b,d,iq])
    return (4*np.pi/(2*k+1))*s
# Note: conj(int psi_b Y^*_kq psi_d) = int psi_b Y_kq psi_d (real psi)
Vr = np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    v = 0
    for k in (2,4):
        v += Fk[k]*ak(k,a,b,c,d)
    Vr[a,b,c,d] = v.real
# spin-orbital indices: idx = 2*alpha + s, s=0 up, 1 down
NSO = 10
def V_so(i,j,k,l):
    ai,si = divmod(i,2); aj,sj = divmod(j,2); ak_,sk = divmod(k,2); al,sl = divmod(l,2)
    if si!=sk or sj!=sl: return 0.0
    return Vr[ai,aj,ak_,al]
Vso = np.zeros((NSO,)*4)
for i,j,k,l in itertools.product(range(NSO),repeat=4):
    Vso[i,j,k,l] = V_so(i,j,k,l)

# ---- Fock space: 7 electrons
dets = []
for occ in itertools.combinations(range(NSO),7):
    m = 0
    for o in occ: m |= 1<<o
    dets.append(m)
dets = sorted(dets)
idx_of = {m:i for i,m in enumerate(dets)}
ND = len(dets)
def occ_list(m): return [i for i in range(NSO) if m>>i &1]

def cdag_c(m, i, j):
    """c_i^dag c_j |m>, returns (sign, newmask) or None"""
    if not (m>>j)&1: return None
    s = (-1)**bin(m & ((1<<j)-1)).count('1')
    m2 = m ^ (1<<j)
    if (m2>>i)&1: return None
    s *= (-1)**bin(m2 & ((1<<i)-1)).count('1')
    m3 = m2 | (1<<i)
    return s, m3

def one_body(h):
    M = np.zeros((ND,ND))
    for n,m in enumerate(dets):
        for i in range(NSO):
            for j in range(NSO):
                if h[i,j]==0: continue
                r = cdag_c(m,i,j)
                if r is None: continue
                s, m3 = r
                M[idx_of[m3], n] += s*h[i,j]
    return M

def two_body(V):
    M = np.zeros((ND,ND))
    for n,m in enumerate(dets):
        occ = occ_list(m)
        for k,l,i,j in itertools.product(range(NSO),repeat=4):
            # (1/2) V_{ijkl} c_i^dag c_j^dag c_l c_k
            v = V[i,j,k,l]
            if v==0: continue
            # apply c_k then c_l then c_j^dag then c_i^dag
            s = 1; mm = m
            if not (mm>>k)&1: continue
            s *= (-1)**bin(mm & ((1<<k)-1)).count('1'); mm ^= 1<<k
            if not (mm>>l)&1: continue
            s *= (-1)**bin(mm & ((1<<l)-1)).count('1'); mm ^= 1<<l
            if (mm>>j)&1: continue
            s *= (-1)**bin(mm & ((1<<j)-1)).count('1'); mm |= 1<<j
            if (mm>>i)&1: continue
            s *= (-1)**bin(mm & ((1<<i)-1)).count('1'); mm |= 1<<i
            M[idx_of[mm], n] += 0.5*s*v
    return M

Hee = two_body(Vso)
# cubic field, unit Dq: z2,x2-y2 -> +6 ; t2g -> -4
ecf = np.array([6,6,-4,-4,-4.0])
hcf = np.diag([ecf[i//2] for i in range(NSO)])
Hcf = one_body(hcf)

# ---- spin operators
Ep = np.zeros((NSO,NSO)); Em = np.zeros((NSO,NSO)); Sz1 = np.zeros((NSO,NSO))
for a in range(5):
    Ep[2*a, 2*a+1] = 1   # c_up^dag c_down
    Em[2*a+1, 2*a] = 1
    Sz1[2*a,2*a] = 0.5; Sz1[2*a+1,2*a+1] = -0.5
Sp = one_body(Ep); Sm = one_body(Em); Sz = one_body(Sz1)
S2 = Sm@Sp + Sz@Sz + Sz
# ---- orbital generators (real basis) from rotations
def rot(axis, th):
    axis = np.array(axis,float); axis/=np.linalg.norm(axis)
    K = np.array([[0,-axis[2],axis[1]],[axis[2],0,-axis[0]],[-axis[1],axis[0],0]])
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K
Psi_pts = psi(P[::7])  # sample points
def Dmat(R):
    Pr = P[::7] @ R.T   # points R r
    Psir = psi(Pr)
    D, *_ = np.linalg.lstsq(Psi_pts, Psir, rcond=None)
    return D
hh = 1e-5
Gs = []
for ax in ([1,0,0],[0,1,0],[0,0,1]):
    Gs.append((Dmat(rot(ax,hh))-Dmat(rot(ax,-hh)))/(2*hh))
Lr = [one_body(np.kron(G, np.eye(2))) for G in Gs]  # acts on spin-orbitals
L2 = -(Lr[0]@Lr[0]+Lr[1]@Lr[1]+Lr[2]@Lr[2])

# ---- group O elements as 3x3 matrices
C4 = np.array([[0,-1,0],[1,0,0],[0,0,1.]])
C3 = np.array([[0,0,1],[1,0,0],[0,1,0.]])
els = [np.eye(3)]
changed=True
while changed:
    changed=False
    for g in list(els):
        for h in (C4,C3):
            n = g@h
            if not any(np.allclose(n,e) for e in els):
                els.append(n); changed=True
assert len(els)==24, len(els)
def cls(R):
    t = np.trace(R)
    if np.allclose(R,np.eye(3)): return 'E'
    if abs(t-0)<1e-9: return 'C3'
    if abs(t-1)<1e-9: return 'C4'
    if abs(t+1)<1e-9:
        return 'C2' if np.allclose(R, np.diag(np.diag(R))) else "C2'"
classes = [cls(R) for R in els]
from collections import Counter
print(Counter(classes))
order = ['E','C3','C2','C4',"C2'"]
irreps = {
 'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
dim = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
chi_of = {'A1':{},'A2':{},'E':{},'T1':{},'T2':{}}
for name,vals in irreps.items():
    for c,v in zip(order,vals):
        chi_of[name][c]=v

# many-body rep of each group element
def many_body(D):
    # W in spin-orbital basis: W[2a+s,2b+s] = D[a,b]
    W1 = np.kron(D, np.eye(2))
    Sl = np.array([occ_list(m) for m in dets])  # ND x 7
    Mx = np.zeros((ND,ND))
    sub = W1[Sl[:,None,:,None], Sl[None,:,None,:]]  # ND x ND x 7 x 7
    return np.linalg.det(sub)
Us = []
for R in els:
    D = Dmat(R)
    Us.append(many_body(D))
Us = np.array(Us)
# sanity: homomorphism check on a couple elements
i1, i2 = 1, 2
