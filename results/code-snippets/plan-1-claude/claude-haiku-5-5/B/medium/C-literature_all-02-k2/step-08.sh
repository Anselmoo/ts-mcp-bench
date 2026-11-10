cd / ; python3 - << 'EOF'
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
# J for m=2,m=-2 pair (direct) and k=0 check
print("k0 same:", ang(2,-2,2,-2,0), " expect 1")
print("k2 (2,2|2,2):", ang(2,2,2,2,2), " expect 2/7*? ")
# Known: F2 coefficient for d_{2}d_{2} self-interaction = 2/7 *? check sum rule: sum_k ang_k should equal 1/(...)
for k in (0,2,4): print(k, ang(0,0,0,0,k))
EOF