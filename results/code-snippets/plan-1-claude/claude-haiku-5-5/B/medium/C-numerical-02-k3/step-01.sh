
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq, least_squares
# angular grid
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
# real d orbitals (unnormalized forms, normalized numerically)
def Ylm(l,m): return sph_harm(m, l, PH, TH)  # scipy: sph_harm(m,n,azimuth,polar)
r = {}
r['xy']  = np.sqrt(15/(4*np.pi))*X*Y
r['yz']  = np.sqrt(15/(4*np.pi))*Y*Z
r['zx']  = np.sqrt(15/(4*np.pi))*Z*X
r['x2y2']= np.sqrt(15/(16*np.pi))*(X**2-Y**2)
r['z2']  = np.sqrt(5/(16*np.pi))*(3*Z**2-1)
names = ['xy','yz','zx','x2y2','z2']
for a in names:
    print(a, np.sum(W*r[a]**2).round(6))
# multipole moments M[k,q][a,c] = \int phi_a phi_c Y_kq^* dOmega
M = {}
for k in [0,2,4]:
    for q in range(-k,k+1):
        Yk = np.conj(Ylm(k,q))
        M[(k,q)] = np.array([[np.sum(W*r[a]*r[c]*Yk) for c in names] for a in names])
# two-electron integrals in units of F^k: V[a,b,c,d] = <ab|1/r12|cd> = sum_k a_k F^k
nb=5
A = {k: np.zeros((nb,nb,nb,nb)) for k in [0,2,4]}
for k in [0,2,4]:
    for q in range(-k,k+1):
        Mq = M[(k,q)]
        # <a|c> density pairs: 1 with (a,c), 2 with (b,d): coefficient 4pi/(2k+1) * M_ac * conj(M_bd)? 
        # V = sum_q int phi_a(1)phi_c(1) Y_kq*(1) * int phi_b(2)phi_d(2) Y_kq(2)
        Mq2 = np.array([[np.sum(W*r[b]*r[d]*Ylm(k,q)) for d in names] for b in names])
        A[k] += 4*np.pi/(2*k+1) * np.einsum('ac,bd->abcd', Mq, Mq2)
# Build Fock space: spin orbitals index i = orb*2 + s (s=0 up,1 down)
N = 10
def apply_cdag_c(state, i, j):
    # returns (sign, newstate) for a_i^dag a_j
    pass
def apply_ops(occ, ops):
    # occ: tuple sorted list of occupied spin orbitals; ops list of ('c',i) or ('a',i) applied right-to-left
    s = list(occ); sign = 1
    for typ, i in reversed(ops):
        if typ == 'a':  # annihilate
            if i not in s: return 0, None
            p = s.index(i); sign *= (-1)**p; s.pop(p)
        else:
            if i in s: return 0, None
            # insert
            p = sum(1 for x in s if x < i); sign *= (-1)**p; s.insert(p, i)
    return sign, tuple(s)
def build(nel, Ve, onebody):
    states = [tuple(c) for c in itertools.combinations(range(N), nel)]
    idx = {s:i for i,s in enumerate(states)}
    H = np.zeros((len(states),len(states)))
    for si, s in enumerate(states):
        # one-body
        for i in range(N):
            for j in range(N):
                if onebody[i,j]==0: continue
                sg, t = apply_ops(s, [('c',i),('a',j)])
                if t is not None: H[idx[t], si] += sg*onebody[i,j]
        # two-body: 1/2 sum V_{abcd} a+_a a+_b a_d a_c, with V_{abcd}=<ab|cd>
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for d in range(N):
                        v = Ve[a,b,c,d]
                        if abs(v)<1e-12: continue
                        sg, t = apply_ops(s, [('c',a),('c',b),('a',d),('a',c)])
                        if t is not None: H[idx[t], si] += 0.5*sg*v
    return H, states
EOF
echo ok