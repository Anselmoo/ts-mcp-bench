import numpy as np
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2
def ang(k,m1,q,m2):
    if m1!=m2+q: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m1)*float(wigner_3j(l,k,l,-m1,q,m2))*red
ms=list(range(-2,3))
W=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        W[i,j]=ang(4,m1,0,m2)+sqrt(5/14)*(ang(4,m1,4,m2)+ang(4,m1,-4,m2))
print(np.round(np.linalg.eigvalsh(W),5))
