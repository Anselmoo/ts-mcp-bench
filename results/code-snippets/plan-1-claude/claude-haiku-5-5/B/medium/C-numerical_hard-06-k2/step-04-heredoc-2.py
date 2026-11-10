import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
ms=[-2,-1,0,1,2]
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def ang(k,m,q,mp):
    if abs(q)>k or abs(m)>l or abs(mp)>l: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def g(k,m1,m2,m3,m4):
    return sum((-1)**q*ang(k,m1,-q,m3)*ang(k,m2,q,m4) for q in range(-k,k+1))
def Vspat(F):
    V=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        m1,m2,m3,m4=ms[a],ms[b],ms[c],ms[d]
        if m1+m2!=m3+m4: continue
        V[a,b,c,d]=sum(Fk*g(k,m1,m2,m3,m4) for k,Fk in ((2,F[2]),(4,F[4])))
    return V
# check: F2 only gives known d-orbital integrals; check spin-orbit free: test Vspat symmetry
V=Vspat({2:1.0,4:0.0})
print("sym", np.allclose(V,V.transpose(1,0,2,3)), np.allclose(V,V.transpose(2,3,0,1)))
