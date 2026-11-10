mkdir -p /work && cat > /work/ts.py << 'EOF'
import numpy as np, itertools, hashlib
from scipy.linalg import expm
from sympy.physics.wigner import wigner_3j
from functools import lru_cache

l = 2
B = 1.0
C = 2511.0/551.0           # in units of B
F2 = 49*B + 7*C            # Racah: F2 = 49B + 7C
F4 = 441*C/35.0            # F4 = 441C/35
Fk = {0: 0.0, 2: F2, 4: F4}

# spin-orbital index: idx = 2*(m+2) + s, s=0 up, 1 down
NSO = 10
def mof(i): return i//2 - 2
def sof(i): return i % 2

@lru_cache(None)
def w3(a,b,c,d,e,f):
    return float(wigner_3j(a,b,c,d,e,f))

def Cel(k, ma, mc):
    """<l ma | C^k_q | l mc>, returns dict q->value (q = ma - mc fixed)"""
    q = ma - mc
    if abs(q) > k: return 0.0
    return (-1)**ma * (2*l+1) * w3(l,k,l,-ma,q,mc) * w3(l,k,l,0,0,0)

# two-electron matrix element <ab|V|cd> (spin-orbitals)
def Vel(a,b,c,d):
    if sof(a)!=sof(c) or sof(b)!=sof(d): return 0.0
    ma, mb, mc, md = mof(a), mof(b), mof(c), mof(d)
    tot = 0.0
    for k,Fv in Fk.items():
        if Fv == 0.0: continue
        s = 0.0
        for q in range(-k,k+1):
            # <a|C^k_q|c> needs q = ma-mc ; <b|C^k_{-q}|d> needs -q = mb-md
            if q != ma-mc or -q != mb-md: continue
            s += (-1)**q * Cel(k,ma,mc) * Cel(k,mb,md)
        tot += Fv*s
    return tot

# Fock space (1024) with Jordan-Wigner
D = 2**NSO
import scipy.sparse as sp
def annih(i):
    rows=[]; cols=[]; vals=[]
    for n in range(D):
        if (n>>i)&1:
            sign = (-1)**bin(n & ((1<<i)-1)).count('1')
            rows.append(n ^ (1<<i)); cols.append(n); vals.append(sign)
    return sp.csr_matrix((vals,(rows,cols)),shape=(D,D),dtype=float)
c = [annih(i) for i in range(NSO)]
cd = [x.T.tocsr() for x in c]
Nocc = sum(cd[i]@c[i] for i in range(NSO))

# basis of N=6 states
idx6 = [n for n in range(D) if bin(n).count('1')==6]
def restrict(M):
    return M[idx6][:,idx6].toarray()

# S^2 operator
Sz = 0.5*sum(cd[i]@c[i]*(1 if sof(i)==0 else -1) for i in range(NSO))
Sp = sum(cd[2*m]@c[2*m+1] for m in range(5))  # up-down: c†_up c_down
Sm = Sp.T.tocsr()
S2 = Sz@Sz + 0.5*(Sp@Sm + Sm@Sp)
S2_6 = restrict(S2)

# single-particle one-body operators (spin-independent): h_mm'
def one_body_op(h):
    """h: 5x5 matrix in m basis (index m+2)"""
    M = sp.csr_matrix((D,D))
    for m in range(-2,3):
        for mp in range(-2,3):
            v = h[m+2, mp+2]
            if abs(v) < 1e-14: continue
            for s in (0,1):
                i = 2*(m+2)+s; j = 2*(mp+2)+s
                M = M + v * (cd[i]@c[j])
    return M

# eg projector in m basis: |0>, (|2>+|-2>)/sqrt2
Peg = np.zeros((5,5),dtype=complex)
Peg[2,2] = 1.0
for a in (2,-2):
    for b in (2,-2):
        Peg[a+2,b+2] += 0.5
# Hamiltonian pieces
# two-body
V2 = np.zeros((D,D))  # placeholder not used
H2 = sp.csr_matrix((D,D))
for a,b,cc,dd in itertools.product(range(NSO),repeat=4):
    v = Vel(a,b,cc,dd)
    if abs(v) < 1e-14: continue
    H2 = H2 + 0.5*v*(cd[a]@cd[b]@c[dd]@c[cc])
H2_6 = restrict(H2)

# single-particle L matrices
def Lmats():
    Lz = np.diag([float(m) for m in range(-2,3)]).astype(complex)
    Lp = np.zeros((5,5),dtype=complex)
    for m in range(-2,2):
        Lp[m+3, m+2] = np.sqrt(l*(l+1)-m*(m+1))
    Lm = Lp.conj().T
    Lx = (Lp+Lm)/2; Ly = (Lp-Lm)/(2j)
    return Lx,Ly,Lz
Lx,Ly,Lz = Lmats()
def op_from_single(h):
    return restrict(one_body_op(h))

Lx_6 = op_from_single(Lx); Ly_6 = op_from_single(Ly); Lz_6 = op_from_single(Lz)

# group rotation unitaries on N=6 space: U = expm(-i theta n.L)
def rot(axis, theta):
    n = np.array(axis,float); n = n/np.linalg.norm(n)
    G = n[0]*Lx_6 + n[1]*Ly_6 + n[2]*Lz_6
    return expm(-1j*theta*G)

group = []  # (class, U)
group.append(('E', rot([0,0,1],0.0)))
for a in [(1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1)]:
    for th in (2*np.pi/3, -2*np.pi/3):
        group.append(('C3', rot(a,th)))
for a in [(1,0,0),(0,1,0),(0,0,1)]:
    group.append(('C2', rot(a,np.pi)))
for a in [(1,0,0),(0,1,0),(0,0,1)]:
    for th in (np.pi/2, -np.pi/2):
        group.append(('C4', rot(a,th)))
for a in [(1,1,0),(1,-1,0),(1,0,1),(1,0,-1),(0,1,1),(0,1,-1)]:
    group.append(('C2p', rot(a,np.pi)))
assert len(group)==24

# O character table
classes = ['E','C3','C2','C4','C2p']
csize = {'E':1,'C3':8,'C2':3,'C4':6,'C2p':6}
chartab = {
 'A1': {'E':1,'C3':1,'C2':1,'C4':1,'C2p':1},
 'A2': {'E':1,'C3':1,'C2':1,'C4':-1,'C2p':-1},
 'E' : {'E':2,'C3':-1,'C2':2,'C4':0,'C2p':0},
 'T1': {'E':3,'C3':0,'C2':-1,'C4':1,'C2p':-1},
 'T2': {'E':3,'C3':0,'C2':-1,'C4':-1,'C2p':1},
}
dimIrr = {'A1':1,'A2':1,'E':2,'T1':3,'T2':3}

# check that U's commute with the N=6 S2 (sanity) and with H later
def label_irreps(V, S):
    """V: columns orthonormal eigvecs of a cluster (same S). returns dict irrep->multiplicity (orbital)"""
    d = V.shape[1]
    chi = {}
    for cl_g,(cls,U) in enumerate(group):
        chi.setdefault(cls, 0)
        chi[cls] += np.trace(V.conj().T @ U @ V)
    out = {}
    for name in chartab:
        s = 0
        for cls in classes:
            s += csize[cls]*chi[cls]*chartab[name][cls]
        mult = s/24.0
        mult = mult/(2*S+1)
        if abs(mult) > 1e-6:
            out[name] = int(round(mult.real))
    return out

LAM = 1000.0
def spectrum(Dq):
    h = -4*Dq*np.eye(5) + 10*Dq*Peg
    H1 = op_from_single(h)
    Htot = H1 + H2_6 + LAM*S2_6
    Htot = (Htot + Htot.conj().T)/2
    w, Vv = np.linalg.eigh(Htot)
    terms = []
    # spin of each eigenvector
    Svals = np.real(np.einsum('ij,ik,kj->j', Vv.conj(), S2_6, Vv))
    Sspin = {}
    for j in range(len(w)):
        Ss = (-1+np.sqrt(1+4*Svals[j]))/2
        Sspin[j] = int(round(Ss))
    # group eigenvalues by (spin, E_H)
    EH = {}
    for j in range(len(w)):
        S = Sspin[j]
        EH[j] = w[j] - LAM*S*(S+1)
    order = sorted(range(len(w)), key=lambda j: EH[j])
    clusters = []
    for j in order:
        if clusters and abs(EH[j]-EH[clusters[-1][0]])<1e-6 and Sspin[j]==Sspin[clusters[-1][0]]:
            clusters[-1].append(j)
        else:
            clusters.append([j])
    levels = []
    for cl in clusters:
        S = Sspin[cl[0]]
        V = Vv[:,cl]
        ir = label_irreps(V, S)
        E = EH[cl[0]]
        for name,mult in ir.items():
            for _ in range(mult):
                levels.append((E, f"{2*S+1}{name}g"))
    levels.sort(key=lambda t: t[0])
    return levels

if __name__ == '__main__':
    import sys
    # sanity at Dq=0
    lv = spectrum(0.0)
    print("Dq=0 levels (count %d):" % len(lv))
    for E,t in lv[:12]: print(f"  {t:8s} {E:.6f}")
    print("Dq = 2 B:")
    for E,t in spectrum(2.0)[:8]: print(f"  {t:8s} {E:.6f}")
EOF
cd /work && time python3 ts.py