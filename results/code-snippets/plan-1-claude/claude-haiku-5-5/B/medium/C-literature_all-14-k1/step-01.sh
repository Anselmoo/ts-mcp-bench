
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from scipy.sparse import csr_matrix, identity, kron
from math import pi, sqrt

# angular grid
nt, npz = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*pi, npz, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.ones(npz)) * (2*pi/npz)
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
# real cubic d orbitals (normalized on sphere): xy,yz,zx,z2,x2-y2
f = [sqrt(15/(4*pi))*X*Y, sqrt(15/(4*pi))*Y*Z, sqrt(15/(4*pi))*X*Z,
     sqrt(5/(16*pi))*(3*Z**2-1), sqrt(15/(16*pi))*(X**2-Y**2)]
names = ['xy','yz','xz','z2','x2y2']
# cubic field energies (relative to barycentre): t2g -4Dq, eg +6Dq (units of Dq)
fieldDq = [-4,-4,-4,6,6]

# Angular coefficients a_k(a,c,b,d)
def ak_table(k):
    A = np.zeros((5,5,5,5))
    for qi in range(-k,k+1):
        Yk = sph_harm(qi, k, PH, TH)  # scipy: sph_harm(m, n, azimuth, polar)
        M = np.array([[np.sum(W*f[a]*f[c]*np.conj(Yk)) for c in range(5)] for a in range(5)])
        N = np.array([[np.sum(W*f[b]*f[d]*Yk) for d in range(5)] for b in range(5)])
        A += np.einsum('ac,bd->acbd', M, N)
    return A*4*pi/(2*k+1)   # indices [a,c,b,d]
A0, A2, A4 = ak_table(0), ak_table(2), ak_table(4)
def Vint(a,b,c,d,F0,F2,F4):
    # <ab|1/r12|cd>
    return F0*A0[a,c,b,d]+F2*A2[a,c,b,d]+F4*A4[a,c,b,d]

# spin orbitals: index = 2*orb + spin (0 up,1 down)
no = 10
# Fock space builder
def build(Dq, F0, F2, F4, Ne=7):
    # one-body and two-body in full Fock space via Jordan-Wigner
    I2 = identity(2, format='csr'); Zm = csr_matrix(np.diag([1.,-1.]))
    a = csr_matrix(np.array([[0,1.],[0,0]]))  # annihilation on single mode: |1>->|0>? basis (0=empty,1=occupied) we use [[0,1],[0,0]]
    def ann(j):
        ops = [Zm]*j + [a] + [I2]*(no-j-1)
        M = ops[0]
        for o in ops[1:]:
            M = kron(M, o, format='csr')
        return M
    c = [ann(j) for j in range(no)]
    cd = [m.T.tocsr() for m in c]
    dim = 2**no
    H = csr_matrix((dim,dim))
    for p in range(no):
        orb, s = divmod(p, 2)
        eps = Dq*fieldDq[orb]
        if eps != 0:
            H = H + eps*(cd[p]@c[p])
    # two-body: 1/2 sum V[ab,cd] a+_a a+_b a_d a_c, with <ab|1/r|cd> spin-diagonal
    for p in range(no):
        for q in range(no):
            op, sp = divmod(p,2); oq, sq = divmod(q,2)
            for r in range(no):
                for s_ in range(no):
                    orr, sr = divmod(r,2); os_, ss = divmod(s_,2)
                    if sp!=sr or sq!=ss: continue
                    if p==q or r==s_: continue
                    v = Vint(op,oq,orr,os_,F0,F2,F4)
                    if abs(v)<1e-12: continue
                    H = H + 0.5*v*(cd[p]@cd[q]@c[s_]@c[r])
    # spin operators
    Sz = sum(0.5*(cd[2*o]@c[2*o]-cd[2*o+1]@c[2*o+1]) for o in range(5))
    Sp = sum(cd[2*o]@c[2*o+1] for o in range(5))
    Sm = Sp.T.tocsr()
    S2 = Sz@Sz + 0.5*(Sp@Sm+Sm@Sp)
    # restrict to N=7
    Nop = sum(cd[p]@c[p] for p in range(no))
    Nd = Nop.diagonal()
    idx = np.where(np.abs(Nd-Ne)<1e-9)[0]
    Hs = H[idx][:,idx].toarray(); S2s = S2[idx][:,idx].toarray()
    return Hs, S2s
EOF
cd /tmp && python3 -c "
import d7
Hs,S2=d7.build(0.0,1,0,0)
import numpy as np
print(np.linalg.eigvalsh(S2).round(3)[:5], Hs.shape)
"