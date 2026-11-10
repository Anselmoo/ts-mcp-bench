import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
# angular grid
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.linspace(0,2*np.pi,nph,endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij')
W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
X = np.sin(TH)*np.cos(PH); Y = np.sin(TH)*np.sin(PH); Z = np.cos(TH)
# real d functions (normalized on sphere)
c = np.sqrt(15/(4*np.pi))
orbs = [c*X*Y, c*Y*Z, c*Z*X, c/2*(X**2-Y**2), np.sqrt(5/(16*np.pi))*(3*Z**2-1)]
# index: 0 xy,1 yz,2 zx (t2g); 3 x2-y2, 4 z2 (eg)
norm = [np.sum(W*f*f) for f in orbs]
orbs = [f/np.sqrt(n) for f,n in zip(orbs,norm)]
# angular coefficients G_K(i,k ; j,l) = 4pi/(2K+1) sum_q [int phi_i phi_k Y_Kq*][int phi_j phi_l Y_Kq]
def Gcoef(i,k,j,l):
    out = {}
    for K in (0,2,4):
        s = 0
        for q in range(-K,K+1):
            Ykq = sph_harm(q, K, PH, TH)
            A = np.sum(W*orbs[i]*orbs[k]*np.conj(Ykq))
            Bv = np.sum(W*orbs[j]*orbs[l]*Ykq)
            s += A*Bv
        out[K] = (4*np.pi/(2*K+1))*s.real
    return out
# spin orbitals: idx = 2*orb + spin (0 up,1 down)
N=10
G = {}
for i,k,j,l in itertools.product(range(5),repeat=4):
    G[(i,k,j,l)] = Gcoef(i,k,j,l)
def build(Dq,B,C):
    F4 = 441*C/35; F2 = (441*B+5*F4)/9
    F = {0:0.0,2:F2,4:F4}
    # one-electron
    h = np.zeros((N,N))
    for o in range(5):
        e = -4*Dq if o<3 else 6*Dq
        for s in range(2): h[2*o+s,2*o+s]=e
    # two-electron integrals g[a,b,c,d] = <ab|1/r|cd> with spin deltas: a(orb i,spin s) etc
    g = np.zeros((N,N,N,N))
    for a,b,cc,d in itertools.product(range(N),repeat=4):
        ia,sa=divmod(a,2); ib,sb=divmod(b,2); ic,sc=divmod(cc,2); id_,sd=divmod(d,2)
        if sa!=sc or sb!=sd: continue
        gg = G[(ia,ic,ib,id_)]
        g[a,b,cc,d] = sum(gg[K]*F[K] for K in (0,2,4))
    # basis: 3-electron determinants
    states = [s for s in itertools.combinations(range(N),3)]
    idx = {s:n for n,s in enumerate(states)}
    M = len(states)
    H = np.zeros((M,M))
    def apply_two(occ, a,b,cc,d):
        # c_a^dag c_b^dag c_c c_d  acting on ordered occupations (tuple sorted)
        pass
    for n,s in enumerate(states):
        occ = list(s)
        # one-electron
        H[n,n] += sum(h[o,o] for o in occ)
        # two-electron: 1/2 sum g_abcd c_a^+ c_b^+ c_d c_c  (<ab|cd>: a,b out; c,d in)
        for p,q,r,t in itertools.product(range(N),repeat=4):
            if g[p,q,r,t]==0: continue
            # operator 1/2 g_{pqrt} c_p^+ c_q^+ c_t c_r
            st = list(occ); sign=1
            # annihilate r then t
            ok=True
            for op,ann in ((r,True),(t,True)):
                pass
            # do: apply c_r then c_t (order: c_p+ c_q+ c_t c_r -> first c_r, then c_t)
            lst=list(st)
            def annih(lst,x):
                if x not in lst: return None,0
                pos=lst.index(x); sg=(-1)**pos; lst.pop(pos); return lst,sg
            lst,s1=annih(lst,r)
            if lst is None: continue
            lst,s2=annih(lst,t)
            if lst is None: continue
            def create(lst,x):
                if x in lst: return None,0
                pos=sum(1 for y in lst if y<x); sg=(-1)**pos; lst.insert(pos,x); lst.sort(); return lst,sg
            lst,s3=create(lst,q)
            if lst is None: continue
            lst,s4=create(lst,p)
            if lst is None: continue
            H[idx[tuple(lst)],n] += 0.5*g[p,q,r,t]*s1*s2*s3*s4
    return H, states
