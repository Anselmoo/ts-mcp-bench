
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > d7.py
import numpy as np
from scipy.special import sph_harm
from scipy.sparse import csr_matrix, identity, kron
from math import pi, sqrt

nt, npz = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*pi, npz, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.ones(npz)) * (2*pi/npz)
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
f = [sqrt(15/(4*pi))*X*Y, sqrt(15/(4*pi))*Y*Z, sqrt(15/(4*pi))*X*Z,
     sqrt(5/(16*pi))*(3*Z**2-1), sqrt(15/(16*pi))*(X**2-Y**2)]
fieldDq = [-4,-4,-4,6,6]

def ak_table(k):
    A = np.zeros((5,5,5,5))
    for qi in range(-k,k+1):
        Yk = sph_harm(qi, k, PH, TH)
        M = np.array([[np.sum(W*f[a]*f[c]*np.conj(Yk)) for c in range(5)] for a in range(5)])
        N = np.array([[np.sum(W*f[b]*f[d]*Yk) for d in range(5)] for b in range(5)])
        A += np.einsum('ac,bd->acbd', M, N)
    return A*4*pi/(2*k+1)
A0, A2, A4 = ak_table(0), ak_table(2), ak_table(4)

no = 10
I2 = identity(2, format='csr')
Zm = csr_matrix(np.diag([1.,-1.]))
am = csr_matrix(np.array([[0,1.],[0,0]]))
def ann(j):
    ops = [Zm]*j + [am] + [I2]*(no-j-1)
    M = ops[0]
    for o in ops[1:]:
        M = kron(M, o, format='csr')
    return M
c = [ann(j) for j in range(no)]
cd = [m.T.tocsr() for m in c]
Nop = sum(cd[p]@c[p] for p in range(no))
idx = np.where(np.abs(Nop.diagonal()-7)<1e-9)[0]
Sz = sum(0.5*(cd[2*o]@c[2*o]-cd[2*o+1]@c[2*o+1]) for o in range(5))
Sp = sum(cd[2*o]@c[2*o+1] for o in range(5)); Sm = Sp.T.tocsr()
S2 = (Sz@Sz + 0.5*(Sp@Sm+Sm@Sp))
S2s = S2[idx][:,idx].toarray()
# one-body (per Dq) and two-body operators (per F_k)
def op_one():
    out=[]
    for orb in range(5):
        out.append(sum(cd[2*orb+s]@c[2*orb+s] for s in range(2)))
    return out
ONE = op_one()
# two-body pieces: T_k = 1/2 sum_{p,q,r,s spin-consistent} A_k[a,c,b,d] a+_p a+_q a_s a_r
TWO = [csr_matrix((len(idx),len(idx))) for _ in range(3)]
def twobody(Ak):
    H = csr_matrix((2**no,2**no))
    for p in range(no):
        for q in range(no):
            if p==q: continue
            op, sp = divmod(p,2); oq, sq = divmod(q,2)
            for r in range(no):
                for s_ in range(no):
                    if s_==r: continue
                    orr, sr = divmod(r,2); os_, ss = divmod(s_,2)
                    if sp!=sr or sq!=ss: continue
                    # electron1: (orbital a=op, c=orr) ; electron2: (b=oq, d=os_)
                    v = Ak[op,orr,oq,os_]
                    if abs(v)<1e-13: continue
                    H = H + 0.5*v*(cd[p]@cd[q]@c[s_]@c[r])
    return H
Ts = [twobody(A) for A in (A0,A2,A4)]
Ts = [T[idx][:,idx].toarray() for T in Ts]
ONEs = [o[idx][:,idx].toarray() for o in ONE]
EOF
cat << 'EOF' > run.py
import numpy as np
from scipy.optimize import least_squares
import d7
F0=1.0
def H(Dq,B,C):
    F2 = 49*B + 7*C; F4 = 63*C/5
    M = sum(Dq*d7.fieldDq[o]*d7.ONEs[o] for o in range(5))
    M = M + d7.Ts[0]*F0 + d7.Ts[1]*F2 + d7.Ts[2]*F4
    return M
# check: Ms=3/2 sector spectrum via S2 eigen
Hm = H(0.0, 1000.0, 4000.0)
# eigen decomposition joint: diagonalize H + mu*S2 to separate spins
mu = 1e5
ev, V = np.linalg.eigh(Hm + mu*d7.S2s)
S2v = np.einsum('ik,ij,jk->k', V, d7.S2s, V)
E = np.einsum('ik,ij,jk->k', V, Hm, V)
for e,s in sorted(zip(E,S2v))[:40]:
    print(round(e,2), round(s,3))
EOF
time python3 run.py | head -60