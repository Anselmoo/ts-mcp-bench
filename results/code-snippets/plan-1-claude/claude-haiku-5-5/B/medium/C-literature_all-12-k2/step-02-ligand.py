import itertools, numpy as np
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from functools import lru_cache
l=2
ms=[-2,-1,0,1,2]
# spin-orbitals: index = 2*orb + s  (s=0 up,1 down)
orbs=[(m,s) for m in ms for s in (0,1)]
@lru_cache(None)
def G(m1,k,q,m3):
    # integral Y_2^{m1*} Y_k^{q*} Y_2^{m3}  (conj on k)  = (-1)^{m1}... use real-free definition
    # Y_k^{q*} = (-1)^q Y_k^{-q}
    return float((-1)**m1 * (-1)**q * gaunt(2,k,2,-m1,-q,m3))
def Vel(m1,m2,m3,m4,Fk):
    # <m1 m2|1/r12|m3 m4> ; Fk dict k->F^k
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            a=G(m1,k,q,m3)
            if a==0: continue
            # electron 2: Y_k^{q}(2) with Y^{m2*}, Y^{m4}: integral Y^{m2*} Y_k^{q} Y^{m4}
            b=float((-1)**m2*gaunt(2,k,2,-m2,q,m4))
            s+=a*b
        tot+=4*pi/(2*k+1)*s*Fk[k]
    return tot
def build(Fk):
    n=10
    # one-electron part handled outside; two-electron operator in spin-orbital basis
    V=np.zeros((n,n,n,n))
    for a in range(n):
        for b in range(n):
            for c in range(n):
                for d in range(n):
                    ma,sa=orbs[a]; mb,sb=orbs[b]; mc,sc=orbs[c]; md,sd=orbs[d]
                    if sa!=sc or sb!=sd: continue
                    V[a,b,c,d]=Vel(ma,mb,mc,md,Fk)
    return V
def states(N):
    out=[]
    for occ in itertools.combinations(range(10),N):
        out.append(occ)
    return out
def hamiltonian(N,Dq,Fk,cf=True):
    V=build(Fk)
    sts=states(N); idx={s:i for i,s in enumerate(sts)}
    H=np.zeros((len(sts),len(sts)))
    for j,s in enumerate(sts):
        occ=list(s)
        # one-electron crystal field: eg (m=0,±2?) -> cubic: in complex basis use tetragonal-free cubic field via Dq
        # handled by Hcf matrix below
        # two-electron: 1/2 sum V[a,b,c,d] a+_a a+_b a_d a_c
        for c_ in range(10):
            for d_ in range(10):
                if c_==d_: continue
                if c_ not in occ: continue
                # annihilate d_? build via loops
        pass
    return None
