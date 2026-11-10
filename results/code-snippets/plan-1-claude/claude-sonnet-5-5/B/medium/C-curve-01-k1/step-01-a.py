import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=821.;C=3657.
F2=49*B+7*C; F4=63*C/5
F={0:0,2:F2,4:F4}
ms=[2,1,0,-1,-2]
def ck(k,m1,m2): # <m1|C^k_q|m2> with q=m1-m2
    q=m1-m2
    from sympy import sqrt,Rational
    return float((-1)**m1*5*gaunt(2,k,2,-m1,q,m2)) if abs(q)<=k else 0.0
# V(m1 m2 m3 m4)=<m1 m2|1/r12|m3 m4> = sum_k F^k c^k(m1,m3) c^k(m4,m2)
def Vee(a,b,c,d):
    s=0
    for k in (2,4):
        if a-c==d-b:  # q conservation
            s+=F[k]/ (1.0) * ck(k,a,c)*ck(k,d,b)/ (1 if True else 1)
    return s
# fix: F^k coefficients c^k includes normalization (2k+1)? use Condon-Shortley c^k(l m,l m')
import sympy
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*sympy.sqrt(5*5)*gaunt(2,k,2,-m1,q,m2)*sympy.sqrt(2*k+1)/sympy.sqrt(4*sympy.pi)*sympy.sqrt(4*sympy.pi)/sympy.sqrt(2*k+1)) if False else float((-1)**m1*5*gaunt(2,k,2,-m1,q,m2)*1)
