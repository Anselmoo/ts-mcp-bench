import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq
# Gauss-Legendre x uniform phi grid for sphere integrals
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph))
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
# real d orbitals (unnormalized forms, normalized numerically)
funcs = {'xy':X*Y,'yz':Y*Z,'xz':X*Z,'x2y2':X**2-Y**2,'z2':3*Z**2-1}
names = list(funcs)
for n in names:
    f = funcs[n]; norm = np.sum(W*f*f); funcs[n] = f/np.sqrt(norm)
def sh(k,q): return sph_harm(q, k, PH, TH)  # scipy: sph_harm(m,n,azimuth,polar)
# angular coefficients ang[k][a][c][b][d] = 4pi/(2k+1) sum_q <a|Y_kq*|c><b|Y_kq|d>
def ang_k(k):
    M = {}
    for q in range(-k,k+1):
        Ykq = sh(k,q)
        Ac = np.array([[np.sum(W*funcs[a]*np.conj(Ykq)*funcs[c]) for c in names] for a in names])
        Bd = np.array([[np.sum(W*funcs[b]*Ykq*funcs[d]) for d in names] for b in names])
        M[q] = (Ac, Bd)
    out = np.zeros((5,5,5,5),dtype=complex)
    for q in M:
        Ac,Bd = M[q]
        out += np.einsum('ac,bd->acbd', Ac, Bd)
    return out*4*np.pi/(2*k+1)
A = {k: ang_k(k).real for k in (0,2,4)}
# spin-orbitals: i = 2*orb + s
N=10; ne=5
states=[sum(1<<i for i in c) for c in itertools.combinations(range(N),ne)]
idx={s:i for i,s in enumerate(states)}
def cdag_c(i,j,s):
    # apply c_i^dag c_j to bitstring s, return (sign, newstate) or None
    if not (s>>j)&1: return None
    sg=1
    s2=s
    # annihilate j
    sg*= (-1)**bin(s2 & ((1<<j)-1)).count('1'); s2 ^= (1<<j)
    if (s2>>i)&1: return None
    sg*= (-1)**bin(s2 & ((1<<i)-1)).count('1'); s2 ^= (1<<i)
    return sg,s2
def build(Dq,B,C):
    # F integrals from B,C: F4=35? use Racah: C=35F4/441, B=(9F2-5F4)/441
    F4 = C*441/35; F2 = (441*B+5*F4)/9; F0=0.0
    # two-electron spatial <pq|rs> = sum_k F^k A_k[p,r,q,s] (p,r: electron1 ; q,s: electron2)
    V = np.zeros((5,5,5,5))
    for k,Fk in ((0,F0),(2,F2),(4,F4)):
        # A[k][a][c][b][d] = <a b|1/r|c d>  -> index a=p, b=q, c=r, d=s
        V += Fk*np.einsum('acbd->abcd', A[k])
    h = np.diag([-4*Dq]*3+[6*Dq]*2)  # xy,yz,xz,x2y2,z2
    # orbital order in names: xy,yz,xz,x2y2,z2 -> t2g first 3
    H = np.zeros((len(states),len(states)))
    so = lambda p,sp: 2*p+sp
    for si,s in enumerate(states):
        for p in range(5):
            for q in range(5):
                if abs(h[p,q])>0:
                    for sp in (0,1):
                        r=cdag_c(so(p,sp),so(q,sp),s)
                        if r: H[idx[r[1]],si]+=h[p,q]*r[0]
        for p,q,r_,s_ in itertools.product(range(5),repeat=4):
            v=V[p,q,r_,s_]
            if abs(v)<1e-12: continue
            for s1 in (0,1):
                for s2 in (0,1):
                    # 1/2 sum <pq|rs> c+_{p s1} c+_{q s2} c_{s_ s2} c_{r_ s1}
                    st=s
                    r1=cdag_c(so(r_,s1),so(q,0),0) # placeholder not used
                    # apply c_{r s1} then c_{s s2} then c+_{q s2} then c+_{p s1}
                    res=[(1,st)]
                    ops=[('a',so(r_,s1)),('a',so(s_,s2)),('c',so(q,s2)),('c',so(p,s1))]
                    sg=1; cur=st; ok=True
                    for typ,o in ops:
                        if typ=='a':
                            if not (cur>>o)&1: ok=False;break
                            sg*=(-1)**bin(cur&((1<<o)-1)).count('1'); cur^=(1<<o)
                        else:
                            if (cur>>o)&1: ok=False;break
                            sg*=(-1)**bin(cur&((1<<o)-1)).count('1'); cur|=(1<<o)
                    if ok:
                        H[idx[cur],si]+=0.5*v*sg
    return H
def S2(Hs):
    pass
