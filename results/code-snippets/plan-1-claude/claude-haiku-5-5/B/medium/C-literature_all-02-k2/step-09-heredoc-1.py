import numpy as np, itertools
from sympy.physics.wigner import gaunt
l=2; ms=list(range(-2,3))
def G(*a): return float(gaunt(*a))
def Ysum(ma,mc,k,q):
    if mc-ma!=q: return 0.0
    return (-1)**(ma+q)*G(l,l,k,-ma,mc,-q)
def Yprod(mb,md,k,q):
    if md-mb!=q: return 0.0
    return (-1)**mb*G(l,l,k,-mb,md,q)
def ang(a,b,c,d,k):
    return 4*np.pi/(2*k+1)*sum(Ysum(a,c,k,q)*Yprod(b,d,k,q) for q in range(-k,k+1))
tr=0
pairs=list(itertools.combinations(ms,2))
for m1,m2 in pairs:
    J=ang(m1,m2,m1,m2,2); K=ang(m1,m2,m2,m1,2)
    tr+=49*(J-K)
print("trace M_S=1 (F2 only, B=1):",tr)
print("expected -35 if E3F=-8,E3P=7")
