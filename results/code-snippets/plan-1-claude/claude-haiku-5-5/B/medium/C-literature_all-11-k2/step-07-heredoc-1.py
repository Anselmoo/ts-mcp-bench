import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2; ms=list(range(-2,3))
def Ck(k,q,m,mp):
    if abs(q)>k: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0)*(2*l+1))
def Acoef(k,m1,m2,m3,m4):
    return sum((-1)**q*Ck(k,q,m1,m3)*Ck(k,-q,m2,m4) for q in range(-k,k+1))
print(Acoef(0,0,0,0,0), Acoef(2,0,0,0,0), Acoef(2,2,-2,2,-2), Acoef(4,2,-2,2,-2))
