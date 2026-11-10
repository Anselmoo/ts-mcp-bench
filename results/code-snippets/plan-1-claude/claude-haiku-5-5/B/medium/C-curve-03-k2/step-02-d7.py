import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def cq(k,q,m,mp):
    # <l m|C^k_q|l mp> with q=m-mp
    if m-mp!=q: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*np.sqrt((2*l+1)*(2*l+1))
def a_k(k,ma,mb,mc,md):
    # <ma mb|1/r12^(k)|mc md> angular part; electron1: ma<-mc, electron2: mb<-md
    s=0.0
    for q in range(-k,k+1):
        s+=(-1)**q*cq(k,-q,ma,mc)*cq(k,q,mb,md)
    return s*(4*np.pi/(2*k+1))/(2*l+1)**0  # normalization fixed below
# Build spin-orbitals
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
def slater_V(F):
    # F: dict k->Fk ; returns function computing <I|V|J> for determinants as sets of spin-orbital indices
    pass
# Calibrate normalization: check Coulomb J for pair (0,0) etc. Use Condon-Shortley: <ab|V|cd> = sum_k F^k a_k(ab;cd)
def Vel(i,j,k_,l_,F):
    # <i j| V | k l> with spin-orbitals i=(m,s) etc.
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=i,j,k_,l_
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (0,2,4):
        if k in F: tot+=F[k]*ak_norm(k,ma,mb,mc,md)
    return tot
def ak_norm(k,ma,mb,mc,md):
    return a_k(k,ma,mb,mc,md)
