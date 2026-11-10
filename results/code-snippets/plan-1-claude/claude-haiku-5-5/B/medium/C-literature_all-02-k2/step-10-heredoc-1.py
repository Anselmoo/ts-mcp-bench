import numpy as np
from sympy.physics.wigner import gaunt, wigner_3j
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
for k in (0,2,4):
    print(k, "sum direct", sum(ang(a,b,a,b,k) for a in ms for b in ms), " sum exch", sum(ang(a,b,b,a,k) for a in ms for b in ms))
print("Gaunt check 000:", G(2,2,2,0,0,0), "expected", np.sqrt(5/(4*np.pi))*float(wigner_3j(2,2,2,0,0,0)))
