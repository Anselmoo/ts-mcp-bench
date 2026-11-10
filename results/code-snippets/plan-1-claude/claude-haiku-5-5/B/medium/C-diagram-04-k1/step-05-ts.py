import numpy as np, itertools, hashlib
from scipy.linalg import expm
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
import scipy.sparse as sp

l = 2
B = 1.0
C = 2511.0/551.0
F2 = 49*B + 7*C
F4 = 441*C/35.0
Fk = {0: 0.0, 2: F2, 4: F4}

NSO = 10
def mof(i): return i//2 - 2
def sof(i): return i % 2

@lru_cache(None)
def w3(a,b,c,d,e,f):
    return float(wigner_3j(a,b,c,d,e,f))

def Cel(k, ma, mc):
    q = ma - mc
    if abs(q) > k: return 0.0
    return (-1)**ma * (2*l+1) * w3(l,k,l,-ma,q,mc) * w3(l,k,l,0,0,0)

def Vel(a,b,c,d):
    if sof(a)!=sof(c) or sof(b)!=sof(d): return 0.0
    ma, mb, mc, md = mof(a), mof(b), mof(c), mof(d)
    tot = 0.0
    for k,Fv in Fk.items():
        if Fv == 0.0: continue
        q = ma-mc
        if abs(q) > k or -q != mb-md: continue
        tot += Fv * (-1)**q * Cel(k,ma,mc) * Cel(k,mb,md)
    return tot

D = 2**NSO
def annih(i):
    rows=[]; cols=[]; vals=[]
    for n in range(D):
        if (n>>i)&1:
            sign = (-1)**bin(n & ((1<<i)-1)).count('1')
            rows.append(n ^ (1<<i)); cols.append(n); vals.append(sign)
    return sp.csr_matrix((vals,(rows,cols)),shape=(D,D),dtype=float)
c = [annih(i) for i in range(NSO)]
cd = [x.T.tocsr() for x in c]

idx6 = [n for n in range(D) if bin(n).count('1')==6]
def restrict(M):
    return np.asarray(M.tocsr()[idx6][:,idx6].todense())

Sz = 0.5*sum((cd[i]@c[i])*(1 if sof(i)==0 else -1) for i in range(NSO))
Sp = sum(cd[2*m]@c[2*m+1] for m in range(5))
Sm = Sp.T.tocsr()
S2 = Sz@Sz + 0.5*(Sp@Sm + Sm@Sp)
S2_6 = restrict(S2)

def one_body_op(h):
    M = sp.csr_matrix((D,D))
    for m in range(-2,3):
        for mp in range(-2,3):
            v = h[m+2, mp+2]
            if abs(v) < 1e-14: continue
            for s in (0,1):
                i = 2*(m+2)+s; j = 2*(mp+2)+s
                M = M + v * (cd[i]@c[j])
    return M

Peg = np.zeros((5,5),dtype=complex)
Peg[2,2] = 1.0
for a in (2,-2):
    for b in (2,-2):
        Peg[a+2,b+2] += 0.5

H2 = sp.csr_matrix((D,D))
for a,b,cc,dd in itertools.product(range(NSO),repeat=4):
    v = Vel(a,b,cc,dd)
    if abs(v) < 1e-14: continue
    H2 = H2 + 0.5*v*(cd[a]@cd[b]@c[dd]@c[cc])
H2_6 = restrict(H2)

Lz = np.diag([float(m) for m in range(-2,3)]).astype(complex)
Lp = np.zeros((5,5),dtype=complex)
for m in range(-2,2):
    Lp[m+3, m+2] = np.sqrt(l*(l+1)-m*(m+1))
Lm = Lp.conj().T
Lx = (Lp+Lm)/2; Ly = (Lp-Lm)/(2j)
Lx_6 = restrict(one_body_op(Lx)); Ly_6 = restrict(one_body_op(Ly)); Lz_6 = restrict(one_body_op(Lz))

def rot(axis, theta):
    n = np.array(axis,float); n = n/np.linalg.norm(n)
    G = n[0]*Lx_6 + n[1]*Ly_6 + n[2]*Lz_6
    return expm(-1j*theta*G)

group = []
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

classes = ['E','C3','C2','C4','C2p']
csize = {'E':1,'C3':8,'C2':3,'C4':6,'C2p':6}
chartab = {
 'A1': {'E':1,'C3':1,'C2':1,'C4':1,'C2p':1},
 'A2': {'E':1,'C3':1,'C2':1,'C4':-1,'C2p':-1},
 'E' : {'E':2,'C3':-1,'C2':2,'C4':0,'C2p':0},
 'T1': {'E':3,'C3':0,'C2':-1,'C4':1,'C2p':-1},
 'T2': {'E':3,'C3':0,'C2':-1,'C4':-1,'C2p':1},
}

def label_irreps(V, S):
    chi = {cl:0 for cl in classes}
    for cls,U in group:
        chi[cls] += np.trace(V.conj().T @ U @ V)
    out = {}
    for name in chartab:
        s = sum(csize[cls]*chi[cls]*chartab[name][cls] for cls in classes)
        mult = s/24.0/(2*S+1)
        if abs(mult) > 1e-6:
            out[name] = int(round(mult.real))
    return out

LAM = 1000.0
def spectrum(Dq):
    h = -4*Dq*np.eye(5) + 10*Dq*Peg
    H1 = restrict(one_body_op(h))
    Htot = H1 + H2_6 + LAM*S2_6
    Htot = (Htot + Htot.conj().T)/2
    w, Vv = np.linalg.eigh(Htot)
    Svals = np.real(np.einsum('ij,ik,kj->j', Vv.conj(), S2_6, Vv))
    Ss = [int(round((-1+np.sqrt(1+4*s))/2)) for s in Svals]
    EH = [w[j] - LAM*Ss[j]*(Ss[j]+1) for j in range(len(w))]
    order = sorted(range(len(w)), key=lambda j: (Ss[j], EH[j]))
    clusters = []
    for j in order:
        if clusters and Ss[j]==Ss[clusters[-1][0]] and abs(EH[j]-EH[clusters[-1][0]])<1e-6:
            clusters[-1].append(j)
        else:
            clusters.append([j])
    levels = []
    for cl in clusters:
        S = Ss[cl[0]]
        V = Vv[:,cl]
        ir = label_irreps(V, S)
        for name,mult in ir.items():
            for _ in range(mult):
                levels.append((EH[cl[0]], f"{2*S+1}{name}g", len(cl)))
    levels.sort(key=lambda t: t[0])
    E0 = levels[0][0]
    return [(E-E0, t, dim) for E,t,dim in levels]

if __name__ == '__main__':
    lv = spectrum(0.0)
    print("Dq=0:", len(lv), "terms")
    for E,t,dim in lv[:10]: print(f"  {t:8s} {E:.6f} dim={dim}")
    for x in [2.0]:
        print("Dq/B =", x)
        for E,t,dim in spectrum(x)[:8]: print(f"  {t:8s} {E:.6f} dim={dim}")
