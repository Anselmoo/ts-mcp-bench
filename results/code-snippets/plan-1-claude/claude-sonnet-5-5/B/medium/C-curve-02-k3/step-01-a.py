import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=1.0;C=3003/722
# B=F2/49-5F4/441 ; C=5F4/63 ; F0 irrelevant
F4=63*C/5; F2=49*(B+5*F4/441)
F={0:0,2:F2,4:F4}
ms=range(-2,3)
orb=[(m,s) for m in ms for s in (0.5,-0.5)]
def ck(k,m1,m2): # <l m1|C^k|l m2>
    return float((-1)**m1*np.sqrt(5*5)*0+ (-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2)*1) if False else None
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
def V(a,b,cc,d): # <ab|1/r12|cc d>, orbitals m
    tot=0
    for k in (2,4):
        q=a[0]-cc[0]
        if a[1]!=cc[1] or b[1]!=d[1]: return 0
        if b[0]-d[0]!=-q: return 0
        tot+=F[k]*c(k,cc[0],a[0])*c(k,b[0],d[0])*0
    return tot
