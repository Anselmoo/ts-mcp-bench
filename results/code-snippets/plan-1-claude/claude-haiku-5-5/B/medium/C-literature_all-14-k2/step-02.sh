mkdir -p /w && cat > /w/d7.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq, least_squares
# grid on sphere
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
def norm(f): return np.sqrt(np.sum(f*f*W))
# real d functions (angular, normalized over sphere)
funcs = {
 'xy': np.sqrt(15)/2*X*Y*2/2*1, 'yz': None, 'zx': None,
}
f_xy = X*Y; f_yz = Y*Z; f_zx = Z*X
f_x2y2 = (X**2-Y**2); f_z2 = (3*Z**2-1)
orbs = [('t2g',f_xy),('t2g',f_yz),('t2g',f_zx),('eg',f_x2y2),('eg',f_z2)]
orbs = [(s, f/norm(f)) for s,f in orbs]
# check orthonormality
M = np.array([[np.sum(a[1]*b[1]*W) for b in orbs] for a in orbs])
assert np.allclose(M, np.eye(5)), M
eps = np.array([-4.0 if s=='t2g' else 6.0 for s,_ in orbs])  # in units of Dq
# spherical harmonics expansion coefficients M^{kq}[a,c] = int f_a f_c Y_kq^*
def Ykq(k,q,TH,PH): return sph_harm(q,k,PH,TH)  # scipy: sph_harm(m,n,azimuth,polar)
Ang = {}
for k in (0,2,4):
    for q in range(-k,k+1):
        Yc = np.conj(Ykq(k,q,TH,PH))
        Mkq = np.zeros((5,5),complex)
        for a in range(5):
            for c in range(5):
                Mkq[a,c] = np.sum(orbs[a][1]*orbs[c][1]*Yc*W)
        Ang[(k,q)] = Mkq
# V_{ab,cd}(F) = sum_k F^k * 4pi/(2k+1) * sum_q M^{kq}[a,c] conj(M^{kq}[b,d])
G = {k: np.zeros((5,5,5,5),complex) for k in (0,2,4)}
for (k,q),Mkq in Ang.items():
    G[k] += 4*np.pi/(2*k+1) * np.einsum('ac,bd->abcd', Mkq, np.conj(Mkq))
# Slater-Condon check: F0 coefficient should be the 'A' term; ignore
# Fock space: 10 spin-orbitals, index = orbital + 5*spin
nso = 10
states = [sum(1<<i for i in c) for c in itertools.combinations(range(nso),7)]
idx = {s:i for i,s in enumerate(states)}
def apply_cdag_c(state, i, j):
    # a_i^dag a_j
    if not (state>>j)&1: return None,0
    s = state & ~(1<<j); sign = (-1)**bin(s & ((1<<j)-1)).count('1')
    if (s>>i)&1: return None,0
    sign *= (-1)**bin(s & ((1<<i)-1)).count('1')
    s |= (1<<i)
    return s, sign
def ops_two(state, a,b,c,d):
    # a_a^dag a_b^dag a_c a_d  (note: a_d first? we use a†_a a†_b a_c a_d ordering)
    s, sg = state, 1
    # apply a_d
    def ann(st,i):
        if not (st>>i)&1: return None,0
        sign=(-1)**bin(st & ((1<<i)-1)).count('1')
        return st & ~(1<<i), sign
    def cre(st,i):
        if (st>>i)&1: return None,0
        sign=(-1)**bin(st & ((1<<i)-1)).count('1')
        return st | (1<<i), sign
    st,s1 = ann(s,d)
    if st is None: return None,0
    st,s2 = ann(st,c)
    if st is None: return None,0
    st,s3 = cre(st,b)
    if st is None: return None,0
    st,s4 = cre(st,a)
    if st is None: return None,0
    return st, s1*s2*s3*s4
def build(B,C,Dq):
    F = {2:49*B+7*C, 4:12.6*C, 0:0.0}
    Vt = {k: G[k]*F[k] for k in (0,2,4)}
    V = sum(Vt.values())  # V[a,b,c,d] = <ab|V|cd>
    n = len(states); H = np.zeros((n,n))
    # one-electron
    for i,s in enumerate(states):
        H[i,i] += sum(Dq*eps[o%5] for o in range(nso) if (s>>o)&1)
    # two-electron: 1/2 sum V_{ab,cd} a†_a a†_b a_d a_c  (spin-orbital)
    def so(o): return o%5, o//5
    for i,s in enumerate(states):
        for a in range(nso):
          for b in range(nso):
            if a==b: continue
            for c in range(nso):
              for d in range(nso):
                if c==d: continue
                oa,sa=so(a); ob,sb=so(b); oc,sc=so(c); od,sd=so(d)
                if sa!=sc or sb!=sd: continue
                v = V[oa,ob,oc,od]
                if abs(v)<1e-12: continue
                st,sg = ops_two(s,a,b,d,c)  # a†_a a†_b a_d a_c : ann c then d
                if st is None: continue
                j = idx[st]
                H[j,i] += 0.5*v*sg
    return H
EOF
cd /w && python3 -c "
import d7,numpy as np
H=d7.build(1,4.5,0)
print(H.shape, np.allclose(H,H.T))
"