import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq, least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]  # spin-orbital index
def G(ma,mc,k,q):
    # <l ma| C^k_q | l mc>
    if ma-mc!=q: return 0.0
    return float((-1)**(l-ma)*(2*l+1)*wigner_3j(l,k,l,-ma,q,mc)*wigner_3j(l,k,l,0,0,0))
def Vint(a,b,c,d,F):
    # <ab|1/r12|cd> spin-orbital
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*G(ma,mc,k,q)*G(mb,md,k,-q)
        tot+=F[k]*s
    return tot
def build(F, dq, withsoc=None):
    N=10
    # one-electron: t2g (m-orbitals not cubic) -> use cubic basis: build via unitary? simpler: use tetragonal-free approach:
    return None
