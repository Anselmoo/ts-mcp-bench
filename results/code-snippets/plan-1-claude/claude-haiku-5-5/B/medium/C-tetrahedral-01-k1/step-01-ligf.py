import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from scipy.linalg import eigh

# angular grid
nt, nph = 120, 240
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.full(nph, 2*np.pi/nph))
rhat = np.stack([np.sin(TH)*np.cos(PH), np.sin(TH)*np.sin(PH), np.cos(TH)], -1)
ms = list(range(-2, 3))
Y = {m: sph_harm(m, 2, PH, TH) for m in ms}   # scipy: sph_harm(m,l,azimuth,polar)

# Td point-charge potential angular matrix (electron-ligand attraction, unit radius)
lig = np.array([[1,1,1],[1,-1,-1],[-1,1,-1],[-1,-1,1]])/np.sqrt(3)
Vang = np.zeros((5,5),complex)
for L in lig:
    d = np.linalg.norm(rhat - L, axis=-1)
    f = -1.0/d
    for i,a in enumerate(ms):
        for j,b in enumerate(ms):
            Vang[i,j] += np.sum(W*np.conj(Y[a])*f*Y[b])
# normalise so that t2 - e splitting = 10 (i.e. h = Dq * Vn, Vn has 10 between t2 and e)
ev = np.linalg.eigvalsh(Vang)
print("raw eig", np.round(ev,4))
# identify e (2 lowest) and t2 (3 highest)
gap = ev[2:].mean() - ev[:2].mean()
Vn = Vang*(10.0/gap)
Vn = Vn - np.eye(5)*np.trace(Vn).real/5  # barycentre zero
print("normalised eig", np.round(np.linalg.eigvalsh(Vn),4))

# Slater-Condon-like angular integrals P_k[a,c,q] = int Y_a^* Y_kq^* Y_c
def Pk(k):
    P = np.zeros((5,5,2*k+1,),complex)
    out = {}
    for q in range(-k,k+1):
        Ykq = sph_harm(q,k,PH,TH)
        M = np.zeros((5,5),complex)
        for i,a in enumerate(ms):
            for j,c in enumerate(ms):
                M[i,j] = np.sum(W*np.conj(Y[a])*np.conj(Ykq)*Y[c])
        out[q]=M
    return out
Pks = {k: Pk(k) for k in (0,2,4)}
# two-electron tensor in units of F^k: V = sum_k F^k * 4pi/(2k+1) sum_q P[a,c,q] P[b,d,q]
def Vtensor(Fk):
    V = np.zeros((5,5,5,5),complex)
    for k in (0,2,4):
        pref = Fk[k]*4*np.pi/(2*k+1)
        for q in range(-k,k+1):
            P = Pks[k][q]
            V += pref*np.einsum('ac,bd->abcd', P, P)
    return V

# spin-orbitals: index = 2*i + s  (s=0 up, 1 down); i over ms
ORB = [(m,s) for m in range(5) for s in (0,1)]
def build(Dq, B, C):
    F4 = 441*C/35.0
    F2 = (441*B + 5*F4)/9.0
    F0 = 0.0   # F0 contributes only constant for d7 (shift), irrelevant to differences
    V5 = Vtensor({0:F0,2:F2,4:F4})
    V5 = V5.real  # integrals are real for real symmetric combos? keep real part
    # full spin-orbital h1 and V2
    n=10
    h = np.zeros((n,n))
    for i,(m,s) in enumerate(ORB):
        for j,(m2,s2) in enumerate(ORB):
            if s==s2: h[i,j] = Dq*Vn[m+2,m2+2].real
    # two-electron: sum_{abcd} 1/2 V[a,c,b,d]-> <ab|cd> a+_a a+_b a_d a_c with spin conservation
    g = np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(ORB):
        for b,(mb,sb) in enumerate(ORB):
            for c,(mc,sc) in enumerate(ORB):
                for d,(md,sd) in enumerate(ORB):
                    if sa==sc and sb==sd:
                        g[a,b,c,d] = V5[ma+2,mb+2,mc+2,md+2]
    # determinants of 7 electrons
    dets = [tuple(sorted(c)) for c in itertools.combinations(range(n),7)]
    idx = {d:i for i,d in enumerate(dets)}
    N=len(dets); H=np.zeros((N,N))
    def apply_ops(state, ops):
        # ops list of (type,orb) applied right to left; state as list of occupied sorted
        occ = list(state); sign=1
        for typ,o in reversed(ops):
            if typ=='a':   # annihilate
                if o not in occ: return None,0
                p = occ.index(o); sign *= (-1)**p; occ.pop(p)
            else:          # create
                if o in occ: return None,0
                p = sum(1 for x in occ if x<o); sign *= (-1)**p; occ.insert(p,o)
        return tuple(occ), sign
    for I,st in enumerate(dets):
        # one-electron
        for p in range(n):
            for q in range(n):
                if h[p,q]==0: continue
                new,sg = apply_ops(st,[('c',p),('a',q)])
                if new is not None and new in idx:
                    H[idx[new],I] += sg*h[p,q]
        # two-electron 1/2 sum g[a,b,c,d] a+_a a+_b a_d a_c
        for a in range(n):
            for b in range(n):
                for c in range(n):
                    for d in range(n):
                        if g[a,b,c,d]==0: continue
                        new,sg = apply_ops(st,[('c',a),('c',b),('a',d),('a',c)])
                        if new is not None:
                            H[idx[new],I] += 0.5*sg*g[a,b,c,d]
    return H, dets

if __name__=="__main__":
    H,dets = build(1.0,0.0,0.0)
    print("ok", H.shape)
