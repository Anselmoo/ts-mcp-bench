mkdir -p /tmp/w && cd /tmp/w && cat > ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y, eval_legendre

x, wx = np.polynomial.legendre.leggauss(24)
nphi = 48
phis = np.arange(nphi)*2*np.pi/nphi
th = np.arccos(x)
TH, PH = np.meshgrid(th, phis, indexing='ij')
W = (np.outer(wx, np.ones(nphi))*2*np.pi/nphi).ravel()
TH = TH.ravel(); PH = PH.ravel()
n = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)],1)
ms = [-2,-1,0,1,2]
Y = np.array([sph_harm_y(2, m, TH, PH) for m in ms])
G = np.clip(n@n.T, -1, 1)
A = {}
for k in (0,2,4):
    P = eval_legendre(k, G)
    M1 = np.conj(Y)[:,None,:]*Y[None,:,:]*W[None,None,:]
    A[k] = np.einsum('abp,pq,cdq->abcd', M1, P, M1)
assert np.allclose(A[0], np.einsum('ab,cd->abcd', np.eye(5), np.eye(5)), atol=1e-8)

norb = 10
def sidx(mi, s): return 2*mi+s
def Vmat(F2, F4):
    V = np.zeros((norb,)*4, dtype=complex)
    for a,b,c,d in itertools.product(range(5), repeat=4):
        ang = F2*A[2][a,c,b,d] + F4*A[4][a,c,b,d]
        for sa in (0,1):
            for sb in (0,1):
                V[sidx(a,sa), sidx(b,sb), sidx(c,sa), sidx(d,sb)] = ang
    return V
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

def cdag_c(p, q, occ):
    """c+_p c_q on sorted tuple occ -> (sign, newocc) or None"""
    occ = list(occ)
    if q not in occ: return None
    pos = occ.index(q); sign = (-1)**pos
    occ.pop(pos)
    if p in occ: return None
    pos2 = sum(1 for x in occ if x < p); sign *= (-1)**pos2
    occ.insert(pos2, p)
    return sign, tuple(occ)

def cdag(p, occ):
    if p in occ: return None
    occ = list(occ); pos = sum(1 for x in occ if x<p)
    occ.insert(pos,p); return (-1)**pos, tuple(occ)
def c(q, occ):
    if q not in occ: return None
    pos = occ.index(q); occ2 = occ[:pos]+occ[pos+1:]
    return (-1)**pos, tuple(occ2)

dets = list(itertools.combinations(range(norb), 7))
index = {d:i for i,d in enumerate(dets)}
N = len(dets)

def build_H(Dq, B, C):
    F4 = 441*C/35; F2 = (441*B+5*F4)/9
    h = hmat(Dq); V = Vmat(F2, F4)
    H = np.zeros((N,N), complex)
    for j,d in enumerate(dets):
        # one-body
        for p in range(norb):
            for q in range(norb):
                if abs(h[p,q])<1e-14: continue
                r = cdag_c(p,q,d)
                if r is None: continue
                s,nd = r
                H[index[nd], j] += s*h[p,q]
        # two-body: 1/2 sum V[p,q,r,s] c+_p c+_q c_s c_r
        for r_ in range(norb):
            a1 = c(r_, d)
            if a1 is None: continue
            sg1, o1 = a1
            for s_ in range(norb):
                a2 = c(s_, o1)
                if a2 is None: continue
                sg2, o2 = a2
                for q in range(norb):
                    a3 = cdag(q, o2)
                    if a3 is None: continue
                    sg3, o3 = a3
                    for p in range(norb):
                        v = V[p,q,r_,s_]
                        if abs(v)<1e-14: continue
                        a4 = cdag(p, o3)
                        if a4 is None: continue
                        sg4, o4 = a4
                        H[index[o4], j] += 0.5*sg1*sg2*sg3*sg4*v
    return H

Sz = np.zeros((N,N)); Sp = np.zeros((N,N))
for j,d in enumerate(dets):
    Sz[j,j] = 0.5*sum(1 if (x%2==0) else -1 for x in d)
    for mi in range(5):
        a = c(sidx(mi,1), d)
        if a is None: continue
        s1,o = a
        b = cdag(sidx(mi,0), o)
        if b is None: continue
        s2,o2 = b
        Sp[index[o2], j] += s1*s2
Sm = Sp.T
S2 = Sz@Sz + 0.5*(Sp@Sm+Sm@Sp)

def levels(Dq, B, C):
    H = build_H(Dq,B,C)
    H = 0.5*(H+H.conj().T).real
    w, v = np.linalg.eigh(H)
    s2 = np.einsum('ij,ik,kj->j', v, S2, v)
    quart = np.array(sorted([wi for wi,s in zip(w,s2) if abs(s-15/4)<1e-5]))
    doub = np.array(sorted([wi for wi,s in zip(w,s2) if abs(s-3/4)<1e-5]))
    return quart, doub
EOF
python3 -c "
from ts import *
q,d = levels(1000,1000,4000)
print(len(q),len(d))
print(np.round(q-q[0],1))
print(np.round(d-q[0],1))
"