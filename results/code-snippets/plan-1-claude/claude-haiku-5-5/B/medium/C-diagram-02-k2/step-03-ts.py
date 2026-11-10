import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.linalg import expm

l = 2
ms = list(range(-2, 3))
modes = [(m, s) for m in ms for s in (+1, -1)]
NM = len(modes)
def mode_index(m, s): return modes.index((m, s))

def Cme(k, m, q, mp):
    if m != mp + q: return 0.0
    return float((-1)**(l-m) * wigner_3j(l, k, l, -m, q, mp) * (-1)**l * (2*l+1)
                 * wigner_3j(l, k, l, 0, 0, 0))
def Gk(k, ma, mb, mc, md):
    return sum((-1)**q * Cme(k, ma, -q, mc) * Cme(k, mb, q, md) for q in range(-k, k+1))

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

def build(n, B, C):
    F4 = 63*C/5.0; F2 = 49*B + 7*C
    Fk = {2: F2, 4: F4}
    basis = list(itertools.combinations(range(NM), n))
    idx = {s: i for i, s in enumerate(basis)}; D = len(basis)
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
    def onebody(h):
        M = np.zeros((D, D), complex)
        for st in basis:
            j = idx[st]
            for a in range(NM):
                for b in range(NM):
                    ma, sa = modes[a]; mb, sb = modes[b]
                    hv = h[ms.index(ma), ms.index(mb)]
                    if sa != sb or abs(hv) < 1e-14: continue
                    new, sg = apply([(True, a), (False, b)], st)
                    if new is None: continue
                    M[idx[new], j] += hv*sg
        return M
    Sp = np.zeros((D, D))
    for st in basis:
        j = idx[st]
        for m in ms:
            new, sg = apply([(True, mode_index(m, +1)), (False, mode_index(m, -1))], st)
            if new is not None: Sp[idx[new], j] += sg
    Sz = np.zeros((D, D))
    for st in basis:
        j = idx[st]
        Sz[j, j] = sum((0.5 if modes[x][1] > 0 else -0.5) for x in st)
    S2 = Sp.T @ Sp + Sz @ Sz + Sz
    e0 = np.zeros(5); e0[ms.index(0)] = 1
    e2 = np.zeros(5); e2[ms.index(2)] = 1/np.sqrt(2); e2[ms.index(-2)] = 1/np.sqrt(2)
    Peg = np.outer(e0, e0) + np.outer(e2, e2)
    Pt2 = np.eye(5) - Peg
    Hcf = onebody((6.0*Peg - 4.0*Pt2).astype(complex)).real  # coefficient of Dq
    Lz = np.diag([float(m) for m in ms]).astype(complex)
    Lp = np.zeros((5, 5), complex)
    for m in ms:
        if m < 2: Lp[ms.index(m+1), ms.index(m)] = np.sqrt(l*(l+1) - m*(m+1))
    Lm = Lp.conj().T
    Lx = (Lp+Lm)/2; Ly = (Lp-Lm)/(2j)
    def Rot(nv, th):
        nv = np.array(nv, float); nv = nv/np.linalg.norm(nv)
        h = nv[0]*Lx + nv[1]*Ly + nv[2]*Lz
        G = onebody(h)
        return expm(-1j*th*G)
    return dict(D=D, basis=basis, Hee=Hee, Hcf=Hcf, S2=S2, Sz=Sz, Rot=Rot)

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    d = build(n, 1.0, 4.0)
    ev, V = np.linalg.eigh(d['Hee'])
    print(np.round(ev - ev[0], 5))
