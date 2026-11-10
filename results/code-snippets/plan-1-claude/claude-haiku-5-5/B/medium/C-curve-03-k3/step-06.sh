python3 - << 'PYEOF'
import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
C=3699/784
F4=441*C/35; F2=(441+5*F4)/9
Fk={0:0.0,2:F2,4:F4}
ms=list(range(-2,3))
def cmat(m,q,mp,k):
    if m-mp!=q: return 0.0
    return math.sqrt(4*math.pi/(2*k+1))*complex((-1)**m*float(gaunt(2,k,2,-m,q,mp)))
def g(m1,m2,m3,m4):
    out={}
    for k in (0,2,4):
        out[k]=sum((-1)**q*cmat(m1,q,m3,k)*cmat(m2,-q,m4,k) for q in range(-k,k+1))
    return out
# check: the Coulomb matrix element symmetric and Oh: print a few
print(g(0,0,0,0)); print(g(2,-2,2,-2)); print(g(2,-2,0,0))
PYEOF