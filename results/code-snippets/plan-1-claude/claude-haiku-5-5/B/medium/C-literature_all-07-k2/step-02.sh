
mkdir -p ~/w && cd ~/w && cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
from scipy.optimize import least_squares
l=2; ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (1,-1)]
N=len(orbs)
@lru_cache(None)
def G(k,m1,m3,q):
    # <l m1| Y_kq |l m3> = int Y_{l m1}^* Y_{kq} Y_{l m3}
    return complex(gaunt(l,k,l,-m1,q,m3))*(-1)**m1
def ang(k,m1,m3,m2,m4):
    # <m1 m2|P_k|m3 m4>, with 1/r12 = sum 4pi/(2k+1) sum_q Y*_kq(1) Y_kq(2)
    s=0
    for q in range(-k,k+1):
        s+= np.conj(G(k,m1,m3,q)) * G(k,m2,m4,q)  # conj on Y_kq^* at electron 1
    return (s*4*np.pi/(2*k+1)).real
def Vee_full(F):
    V=np.zeros((N,N,N,N))
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
      for a,(m3,s3) in enumerate(orbs):
       for b,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4: continue
        V[i,j,a,b]=sum(Fk*ang(k,m1,m3,m2,m4) for k,Fk in zip((0,2,4),F))
    return V
# build many-electron Hamiltonian in determinant basis, 5 electrons
dets=list(itertools.combinations(range(N),5))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det, ops):
    # ops: list of (type,i) applied right-to-left; returns (sign, newdet) or None
    occ=list(det); sign=1
    for op,i in reversed(ops):
        if op=='a':  # annihilate
            if i not in occ: return None
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            # insert in order
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign, tuple(occ)
def build(F, Dq):
    V=Vee_full(F)
    M=len(dets)
    H=np.zeros((M,M))
    # one-electron cubic field: real basis diag: eg +6Dq, t2g -4Dq. Use complex basis via cubic field matrix
    # build one-body matrix h in complex basis: t2g/eg projection. Use real-basis transformation
    h=np.zeros((5,5),dtype=complex)
    # Real d orbitals in terms of complex |m>: build via unitary
    U=np.zeros((5,5),dtype=complex)  # columns: real orbitals in complex basis
    s2=np.sqrt(2)
    # index by m+2
    # xy, yz, xz, x2-y2, z2
    U[0+2,0]=0  # placeholder
    # standard: |xy>=i/sqrt2 (Y2-2 - Y22), |x2-y2>=1/sqrt2(Y22+Y2-2), |yz>=i/sqrt2(Y21+Y2-1), |xz>=1/sqrt2(Y2-1 - Y21), |z2>=Y20
    def vec(d):
        v=np.zeros(5,dtype=complex)
        for m,c in d.items(): v[m+2]=c
        return v
    orbR=[vec({-2:1j/s2,2:-1j/s2}), vec({2:1/s2,-2:1/s2}), vec({-1:1j/s2,1:1j/s2}), vec({-1:1/s2,1:-1/s2}), vec({0:1})]
    # cubic field: t2g (xy,yz,xz) -4Dq, eg (x2-y2,z2) +6Dq
    hR=np.diag([-4*Dq,-4*Dq,-4*Dq,6*Dq,6*Dq]).astype(complex)
    Uc=np.array(orbR).T  # complex coeffs of real orbitals
    h=Uc@hR@Uc.conj().T   # operator in complex basis
    # one-body
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
        if s1!=s2: continue
        hv=h[m1+2,m2+2]
        if abs(hv)<1e-12: continue
        for d in dets:
            r=apply_ops(d,[('c',i),('a',j)])
            if r is None: continue
            sg,nd=r
            H[idx[nd],idx[d]]+= sg*hv.real if abs(hv.imag)<1e-12 else sg*hv
    # two-body: 1/2 sum V_ijkl c_i^+ c_j^+ c_l c_k  with V_ijkl=<ij|1/r|kl>
    for i in range(N):
     for j in range(N):
      for k in range(N):
       for l_ in range(N):
        v=V[i,j,k,l_]
        if abs(v)<1e-12 or i==j or k==l_: continue
        for d in dets:
            r=apply_ops(d,[('c',i),('c',j),('a',l_),('a',k)])
            if r is None: continue
            sg,nd=r
            H[idx[nd],idx[d]]+=0.5*sg*v
    return H
EOF
cat << 'EOF' > test.py
import numpy as np
from d5 import *
H=build((1.0,0,0),0.0)
w=np.linalg.eigvalsh(H)
import collections
print(collections.Counter(np.round(w,6)))
EOF
timeout 500 python3 test.py
