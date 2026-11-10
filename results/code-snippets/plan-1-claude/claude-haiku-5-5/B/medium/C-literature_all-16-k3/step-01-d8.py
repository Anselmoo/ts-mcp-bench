import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
from math import comb
# --- angular integrals numerically (Gauss-Legendre x uniform phi) ---
nth, nph = 40, 80
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = range(-2, 3)
Y = {m: sph_harm(m, 2, PH, TH) for m in range(-4, 5) for _ in [0]}
def Yk(k,q): return sph_harm(q, k, PH, TH)
orb = [(m,) for m in ms]
# Gaunt-type angular factors ang[k][a,b,c,d] = P1*P2 summed over q
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    Ylm = {m: sph_harm(m,2,PH,TH) for m in ms}
    for q in range(-k,k+1):
        Yq = Yk(k,q)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A
A = {k: ang_k(k) for k in (0,2,4)}
def Vcoul(F0,F2,F4):
    return A[0]*F0 + A[2]*F2 + A[4]*F4
# --- Fock space, 10 spin orbitals: index = 2*i + s, s=0 up,1 down
nso = 10
def cop(i):
    # Jordan-Wigner annihilation on 1024-dim space
    dim = 2**nso
    M = np.zeros((dim,dim))
    for st in range(dim):
        if (st>>i)&1:
            sign = (-1)**bin(st & ((1<<i)-1)).count('1')
            M[st ^ (1<<i), st] = sign
    return M
C = [cop(i) for i in range(nso)]
Cd = [c.T for c in C]
def build(Dq,B,Cc):
    F4 = 12.6*Cc; F2 = 49*B + 7*Cc; F0 = 0.0
    V = Vcoul(F0,F2,F4).real  # real part; check imag small
    # orbital index i = m+2
    h = np.zeros((5,5))
    # cubic: t2g and eg in complex basis
    s2=np.sqrt(2)
    t2g = []
    t2g.append(np.array([0,0,0,0,0],complex))  # placeholder
    v_xy = np.zeros(5,complex); v_xy[4]=1/(1j*s2); v_xy[0]=-1/(1j*s2)
    v_xz = np.zeros(5,complex); v_xz[3]=-1/s2; v_xz[1]=1/s2
    v_yz = np.zeros(5,complex); v_yz[3]=1j/s2; v_yz[1]=1j/s2
    eg = []
    v_z2 = np.zeros(5,complex); v_z2[2]=1
    v_x2 = np.zeros(5,complex); v_x2[4]=1/s2; v_x2[0]=1/s2
    Pt = sum(np.outer(v,v.conj()) for v in (v_xy,v_xz,v_yz))
    Pe = sum(np.outer(v,v.conj()) for v in (v_z2,v_x2))
    hm = -4*Dq*Pt + 6*Dq*Pe
    # full operators
    dim = 2**nso
    H = np.zeros((dim,dim),complex)
    for a in range(5):
        for b in range(5):
            if abs(hm[a,b])>1e-12:
                for s in (0,1):
                    H += hm[a,b]*Cd[2*a+s]@C[2*b+s]
    # two-body: 1/2 sum V_abcd c+_a c+_b c_d c_c, with V=<ab|g|cd>, spin a=c, b=d
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        v = V[a,b,c,d]
        if abs(v)<1e-10: continue
        for s1 in (0,1):
         for s2_ in (0,1):
            H += 0.5*v*(Cd[2*a+s1]@Cd[2*b+s2_]@C[2*d+s2_]@C[2*c+s1])
    return H
# restrict to N=8
Nop = sum(Cd[i]@C[i] for i in range(nso))
diagN = np.real(np.diag(Nop))
idx = np.where(np.abs(diagN-8)<1e-9)[0]
Sz = np.array([ (sum(((st>>(2*i))&1) - ((st>>(2*i+1))&1) for i in range(5))) for st in idx])
print("dim N=8:", len(idx))
def spectrum(Dq,B,Cc):
    H = build(Dq,B,Cc)
    Hs = H[np.ix_(idx,idx)].real
    Ssel = Sz
    # triplet: Sz=2 (nup-ndn)=2 -> Ms=1 ; sectors
    t_idx = np.where(Ssel==2)[0]
    Ht = Hs[np.ix_(t_idx,t_idx)]
    et = np.sort(np.linalg.eigvalsh(Ht))
    z_idx = np.where(Ssel==0)[0]
    Hz = Hs[np.ix_(z_idx,z_idx)]
    ez = np.sort(np.linalg.eigvalsh(Hz))
    # remove triplet eigenvalues from Sz=0
    singlets = list(ez)
    for t in et:
        j = int(np.argmin(np.abs(np.array(singlets)-t)))
        singlets.pop(j)
    return et, np.array(singlets)
et, es = spectrum(1000.0, 1000.0, 4000.0)
print("triplet Ms=1 eig:", np.round(et,3))
print("singlets:", np.round(es,3))
np.save('/tmp/dummy.npy', np.zeros(1))
import pickle
pickle.dump(None, open('/tmp/ok','wb'))
