import numpy as np, itertools
from functools import lru_cache
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve

l=2
ms=list(range(-2,3))
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))

def Ysum(ma,mc,k,q):  # ∫ Y_a* Y_c Y_kq* dΩ
    if mc-ma!=q: return 0.0
    return (-1)**(ma+q)*G(l,l,k,-ma,mc,-q)
def Yprod(mb,md,k,q):  # ∫ Y_b* Y_d Y_kq
    if md-mb!=q: return 0.0
    return (-1)**mb*G(l,l,k,-mb,md,q)

def Oint(ma,mc):
    tot=0.0
    for (q,coef) in [(0,1.0),(4,np.sqrt(5/14)),(-4,np.sqrt(5/14))]:
        if mc-ma+q!=0: continue
        tot+=coef*(-1)**ma*G(l,4,l,-ma,q,mc)
    return tot
Om=np.array([[Oint(a,c) for c in ms] for a in ms])
ev=np.linalg.eigvalsh(Om)
print("cubic eigen (raw):",np.round(ev,6))
