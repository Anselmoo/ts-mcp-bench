cd ~ 2>/dev/null; pwd; touch x_test 2>&1 && echo writable_home; python3 - << 'EOF'
import numpy as np
from functools import lru_cache
from sympy.physics.wigner import gaunt
l=2
ms=list(range(-2,3))
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
def Oint(ma,mc):
    tot=0.0
    for (q,coef) in [(0,1.0),(4,np.sqrt(5/14)),(-4,np.sqrt(5/14))]:
        if mc-ma+q!=0: continue
        tot+=coef*(-1)**ma*G(l,4,l,-ma,q,mc)
    return tot
Om=np.array([[Oint(a,c) for c in ms] for a in ms])
print(np.round(np.linalg.eigvalsh(Om),6))
EOF