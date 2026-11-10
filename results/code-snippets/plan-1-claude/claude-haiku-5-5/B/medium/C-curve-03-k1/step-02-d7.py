import itertools, numpy as np
from sympy.physics.wigner import wigner_3j
from fractions import Fraction
from math import sqrt
l=2
ms=list(range(-2,3))
# spin orbitals: (m, s) s=+1/2 index 0, -1/2 index 1
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
N=len(orbs)
def ang(k,m1,m2,m3,m4):
    # <m1 m2|C^k(1).C^k(2)|m3 m4> angular factor (q = m1-m3)
    q=m1-m3
    if m2-m4!=-q: return 0.0
    if abs(q)>k: return 0.0
    def red(k):
        return float((-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
    def me(m,q_,mp):
        return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q_,mp))*red(k)
    return me(m1,q,m3)*me(m2,-q,m4)
def Vel(i,j,kk,ll,F):
    # <ij|1/r12|kk ll> with spin deltas
    mi,si=orbs[i]; mj,sj=orbs[j]; mk,sk=orbs[kk]; ml,sl=orbs[ll]
    if si!=sk or sj!=sl: return 0.0
    tot=0.0
    for k,Fk in F.items():
        tot+=Fk*ang(k,mi,mj,mk,ml)
    return tot
def build(F):
    # determinants with 7 electrons
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),7)]
    idx={d:n for n,d in enumerate(dets)}
    D=len(dets)
    H=np.zeros((D,D))
    # two-body: 1/2 sum V_ijkl a+_i a+_j a_l a_k
    Vt={}
    for i,j,kk,ll in itertools.product(range(N),repeat=4):
        v=Vel(i,j,kk,ll,F)
        if abs(v)>1e-12: Vt[(i,j,kk,ll)]=v
    def apply_ann(p,st):
        if not (st>>p)&1: return None,0
        sign=(-1)**bin(st&((1<<p)-1)).count('1')
        return st^(1<<p),sign
    def apply_cre(p,st):
        if (st>>p)&1: return None,0
        sign=(-1)**bin(st&((1<<p)-1)).count('1')
        return st|(1<<p),sign
    for n,d in enumerate(dets):
        for (i,j,kk,ll),v in Vt.items():
            # a_k then a_l then a+_j then a+_i : a+_i a+_j a_l a_k
            s1,g1=apply_ann(kk,d)
            if s1 is None: continue
            s2,g2=apply_ann(ll,s1)
            if s2 is None: continue
            s3,g3=apply_cre(j,s2)
            if s3 is None: continue
            s4,g4=apply_cre(i,s3)
            if s4 is None: continue
            H[idx[s4],n]+=0.5*v*g1*g2*g3*g4
    # one-body: 10 Dq P_eg (relative); we return separately
    Peg=np.zeros((D,D))
    for n,d in enumerate(dets):
        for p in range(N):
            m,s=orbs[p]
            if abs(m)==2 or m==0:  # eg: m=0 and (|2>+|-2>)/sqrt2 -> handle below
                pass
    return dets,H
