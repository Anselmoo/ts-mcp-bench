import numpy as np, itertools, sys
from sympy.physics.wigner import wigner_3j
from scipy.linalg import expm, eigh

l = 2
ms = list(range(-2, 3))
modes = [(m, s) for m in ms for s in (+1, -1)]   # 10 spin-orbitals
NM = len(modes)
def mode_index(m, s): return modes.index((m, s))

def Cme(k, m, q, mp):   # <l m | C^k_q | l mp>
    if m != mp + q: return 0.0
    return float((-1)**(l-m) * wigner_3j(l, k, l, -m, q, mp) * (-1)**l * (2*l+1)
                 * wigner_3j(l, k, l, 0, 0, 0))
def Gk(k, ma, mb, mc, md):
    tot = 0.0
    for q in range(-k, k+1):
        tot += (-1)**q * Cme(k, ma, -q, mc) * Cme(k, mb, q, md)
    return tot

def build(n, B, C):
    F4 = 63*C/5.0
    F2 = 49*B + 7*C
    Fk = {0: 0.0, 2: F2, 4: F4}
    # Fock basis with n electrons
    basis = list(itertools.combinations(range(NM), n))
    idx = {s: i for i, s in enumerate(basis)}
    D = len(basis)
    def apply(ops, st):
        occ = list(st); sign = 1
        for dag, mo in reversed(ops):
            below = sum(1 for x in occ if x < mo)
            if dag:
                if mo in occ: return None, 0
                occ.append(mo); occ.sort()
            else:
                if mo not in occ: return None, 0
                occ.remove(mo)
            if below % 2: sign = -sign
        return tuple(occ), sign
    # two-body integrals list
    Vlist = []
    for a, b, c, d in itertools.product(range(NM), repeat=4):
        ma, sa = modes[a]; mb, sb = modes[b]; mc, sc = modes[c]; md, sd = modes[d]
        if sa != sc or sb != sd: continue
        v = sum(Fk[k]*Gk(k, ma, mb, mc, md) for k in (2, 4))
        if abs(v) > 1e-12: Vlist.append((a, b, c, d, v))
    Hee = np.zeros((D, D))
    for st in basis:
        j = idx[st]
        for a, b, c, d, v in Vlist:
            new, sg = apply([(False, c), (False, d), (True, b), (True, a)], st)
            if new is None: continue
            Hee[idx[new], j] += 0.5*v*sg
    # one-body generators
    def onebody(h):   # h: 5x5 in m basis, spin diagonal
        M = np.zeros((D, D))
        for st in basis:
            j = idx[st]
            for a in range(NM):
                for b in range(NM):
                    ma, sa = modes[a]; mb, sb = modes[b]
                    if sa != sb or abs(h[ms.index(ma), ms.index(mb)]) < 1e-14: continue
                    new, sg = apply([(True, a), (False, b)], st)
                    if new is None: continue
                    M[idx[new], j] += h[ms.index(ma), ms.index(mb)]*sg
        return M
    # spin operators
    Sp = np.zeros((D, D)); 
    for st in basis:
        j = idx[st]
        for m in ms:
            new, sg = apply([(True, mode_index(m, +1)), (False, mode_index(m, -1))], st)
            if new is not None: Sp[idx[new], j] += sg
    Sz = np.zeros((D, D))
    for st in basis:
        j = idx[st]
        Sz[j, j] = sum((0.5 if modes[x][1] > 0 else -0.5) for x in st)
    S2 = Sp.T @ Sp + Sz @ Sz + Sz  # S- S+ = S^2 - Sz^2 - Sz  -> S^2 = S-S+ + Sz^2 + Sz ; S- = Sp^T
    S2 = Sp.T @ Sp + Sz @ Sz + Sz
    # cubic field projectors (orbital m basis)
    Peg = np.zeros((5, 5)); 
    e0 = np.zeros(5); e0[ms.index(0)] = 1
    e2 = np.zeros(5); e2[ms.index(2)] = 1/np.sqrt(2); e2[ms.index(-2)] = 1/np.sqrt(2)
    Peg = np.outer(e0, e0) + np.outer(e2, e2)
    Pt2 = np.eye(5) - Peg
    Hcf_unit = onebody(6.0*Peg - 4.0*Pt2)   # coefficient of Dq
    # rotation generators
    Lz = np.diag([float(m) for m in ms]).astype(complex)
    Lp = np.zeros((5, 5), complex)
    for m in ms:
        if m < 2: Lp[ms.index(m+1), ms.index(m)] = np.sqrt(l*(l+1) - m*(m+1))
    Lm = Lp.conj().T
    Lx = (Lp+Lm)/2; Ly = (Lp-Lm)/(2j)
    def Rot(nvec, th):
        nvec = np.array(nvec, float); nvec /= np.linalg.norm(nvec)
        h = nvec[0]*Lx + nvec[1]*Ly + nvec[2]*Lz
        G = onebody(h)  # real? h is complex -> handle
        return G
    return dict(D=D, basis=basis, idx=idx, Hee=Hee, Hcf=Hcf_unit, S2=S2, Sz=Sz,
                Lx=Lx, Ly=Ly, Lz=Lz, onebody=onebody)
