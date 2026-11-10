import numpy as np, itertools
from scipy.optimize import least_squares
from math import factorial
# orbitals: m in -2..2 x spin; octahedral: t2g = xy,yz,xz ; eg = z2,x2-y2
# use real orbitals: index 0..4 real d orbitals; t2g: xy,yz,xz (idx 0,1,2), eg: z2,x2-y2 (3,4)
# Slater integrals via Racah B,C: build Coulomb with Gaunt-like coefficients using complex m basis
from sympy.physics.wigner import wigner_3j
def gaunt(l,k,lp,m,q,mp):
    # angular factor <l m| C^k_q |l' m'> style: (-1)^m sqrt((2l+1)(2lp+1)) 3j(l k lp;0 0 0) 3j(l k lp;-m q mp)
    return (-1)**m*np.sqrt((2*l+1)*(2*lp+1))*float(wigner_3j(l,k,lp,0,0,0))*float(wigner_3j(l,k,lp,-m,q,mp))
ms=[-2,-1,0,1,2]
spin=[0.5,-0.5]
orbs=[(m,s) for m in ms for s in spin]
def ang(k,m1,m2,m3,m4):
    # <m1 m2|1/r12^k|m3 m4> angular part: sum_q (-1)^q ak(m1,m3) ak(m2,m4) with q=m3-m1 etc
    q=m3-m1
    if abs(q)>k or m4-m2!=-q: return 0
    a=gaunt(2,k,2,m1,q,m3)*gaunt(2,k,2,m2,-q,m4)*(-1)**(q)
    return a
def ak_coef(k,m1,m3,m2,m4):
    return ang(k,m1,m2,m3,m4)
# Slater: F0 direct etc. Use F2,F4 via ang with factor 4pi/(2k+1) sum: a_k = 4pi/(2k+1) sum_q ... ; ratio approach: Use standard: <ab|V|cd>= sum_k F^k * c^k(...)
# Use Racah form: c^k = (4pi/(2k+1)) sum_q (-1)^q <l||C^k||l'> ... simply: W(m1,m2,m3,m4)=sum_k F^k * sum_q (-1)^q C(m1,m3,k,q) C(m2,m4,k,-q)
def W(k,m1,m2,m3,m4):
    tot=0
    for q in range(-k,k+1):
        if m3-m1!=q or m4-m2!=-q: continue
        tot+= (-1)**q * gaunt(2,k,2,m1,-q,m3)*gaunt(2,k,2,m2,q,m4)
    return tot
def build(F2,F4):
    dets=list(itertools.combinations(range(10),3))
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets)
    H=np.zeros((N,N))
    F0=0
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            # one-electron part handled separately; Coulomb: sum over pairs
            # <d|V|e> via Slater rules brute
            pass
    return None
