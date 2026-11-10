import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq, minimize
from scipy.linalg import eigh
# grid for sphere
nt, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)  # cos theta
ph = np.arange(nph)*2*np.pi/nph
CT, PH = np.meshgrid(x, ph, indexing='ij')
W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
TH = np.arccos(CT)
ms = [-2,-1,0,1,2]
def Y(l,m,th,phi): return sph_harm(m,l,phi,th)  # scipy: sph_harm(m,n,azimuth,polar)
Yd = {m: Y(2,m,TH,PH) for m in ms}
def integ(f): return np.sum(W*f)
# cubic potential f = x^4+y^4+z^4 (angular part)
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
f = X**4+Yy**4+Z**4 - 0.6
M = np.array([[integ(np.conj(Yd[a])*f*Yd[b]) for b in ms] for a in ms])
ev, U = np.linalg.eigh(M)
# eigenvalues: 2-fold (eg) and 3-fold (t2g); assign: lower 3 -> t2g
ev_sorted = np.sort(ev)
print("cubic eigen", ev_sorted)
# build single-particle h in m basis: t2g -> -4Dq, eg -> +6Dq (per unit Dq)
# H1(a,b) = sum over eigvecs: eg proj*6 - t2g proj*4 ; eigvecs with eigenvalue ~ ratio
idx = np.argsort(ev)
t2 = U[:, idx[:3]]; eg = U[:, idx[3:]]
# ev for t2g are the lower group? check sign: t2g region ev low (f has +/- ) determine by number
# Use proper: cubic f has eg sign opposite; choose group of 3 with ratio -2:3 -> whichever is 3-fold
h_dq = -4*t2@t2.conj().T + 6*eg@eg.conj().T
# orbital index: spin-orbitals 2*i + s, i over ms, s=0 up,1 down
def sp(i,s): return 2*i+s
# Fock space of 10 spin-orbitals, N=4
norb=10
states=[sum(1<<k for k in c) for c in itertools.combinations(range(norb),4)]
index={s:i for i,s in enumerate(states)}
D=len(states)
def cdag_c(i,j):
    # returns matrix of c_i^dag c_j in N=4 subspace
    M=np.zeros((D,D))
    for s in states:
        if not (s>>j)&1: continue
        s1 = s ^ (1<<j)
        sign = (-1)**bin(s1 & ((1<<j)-1)).count('1')
        if (s1>>i)&1: continue
        s2 = s1 | (1<<i)
        sign *= (-1)**bin(s2 & ((1<<i)-1)).count('1')
        M[index[s2], index[s]] += sign
    return M
# one-body
H1 = np.zeros((D,D))
for i in range(5):
    for j in range(5):
        for s in (0,1):
            if abs(h_dq[i,j])>1e-12:
                H1 += h_dq[i,j]*cdag_c(sp(i,s), sp(j,s))
# Slater angular integrals a_k
def ang(k, a, c):  # returns dict q -> <a|Y_kq^* |c> style integrals: int Y_a^* Y_kq^* Y_c
    out={}
    for q in range(-k,k+1):
        out[q] = integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[c])
    return out
def ang2(k,b,d):
    out={}
    for q in range(-k,k+1):
        out[q]= integ(np.conj(Yd[b])*Y(k,q,TH,PH)*Yd[d])
    return out
def akval(k,a,b,c,d):
    # int Y_a*(1)Y_b*(2) (4pi/(2k+1)) sum_q Y_kq*(1)Y_kq(2) Y_c(1)Y_d(2)
    s=0
    for q in range(-k,k+1):
        g1 = integ(np.conj(Yd[a])*np.conj(Y(k,q,TH,PH))*Yd[c])
        g2 = integ(np.conj(Yd[b])*Y(k,q,TH,PH)*Yd[d])
        s+= g1*g2
    return 4*np.pi/(2*k+1)*s
# Build V_ee with F0 and F2,F4 : a_k for k=0,2,4
def build_V(F):
    Hv=np.zeros((D,D))
    # 1/2 sum_{abcd} <ab|v|cd> c_a^+ c_b^+ c_d c_c
    # spin-orbital indices p=(i,s)
    pairs=[(i,s) for i in range(5) for s in (0,1)]
    # precompute ops
    cache={}
    def op(p,q):
        if (p,q) not in cache: cache[(p,q)]=cdag_c(sp(*p),sp(*q)) if False else cdag_c(p,q)
        return cache[(p,q)]
    for (a1,s1) in [(i,s) for i in range(5) for s in (0,1)]:
        pass
    # loop over orbital indices and spins
    ia=[(i,s) for i in range(5) for s in (0,1)]
    for A in range(10):
      for B_ in range(10):
        for C_ in range(10):
          for Dd in range(10):
            ia_,sa=ia[A]; ib,sb=ia[B_]; ic,sc=ia[C_]; idd,sd=ia[Dd]
            if sa!=sc or sb!=sd: continue  # spin conservation
            val=0
            for k,Fk in F.items():
                val+= Fk*akval(k,ia_,ib,ic,idd)
            if abs(val)<1e-12: continue
            # term: 1/2 <ab|v|cd> c_a^+ c_b^+ c_d c_c
            Hv += 0.5*val* (cdag_c(A,B_) @ cdag_c(0,0)*0) if False else 0
    return Hv
