import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=922.;C=4156.
F4=C/35;F2=B+5*F4
ms=range(-2,3)
def c(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,q,m2)*wigner_3j(2,k,2,0,0,0))
# check: <m1 m2|g|m1 m2> direct vs. known: F2 coefficient for m=2,2: 
print(c(2,2,2),c(2,0,0),c(4,0,0))
