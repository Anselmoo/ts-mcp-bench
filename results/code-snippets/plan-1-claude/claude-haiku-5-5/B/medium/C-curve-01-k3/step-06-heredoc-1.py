import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2; ms=list(range(-2,3))
def red(k): return (-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
def C(k,q,m,mp):
    if m!=mp+q: return 0.0
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*red(k)
def ang(k,a,c,b,d):
    return sum((-1)**q*C(k,q,a,c)*C(k,-q,b,d) for q in range(-k,k+1))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
print("ang0", ang(0,2,2,-2,-2), ang(0,0,0,0,0))
print("ang2 (2,2;2,2)", ang(2,2,2,2,2), "ang4", ang(4,2,2,2,2), ang(4,0,0,0,0))
