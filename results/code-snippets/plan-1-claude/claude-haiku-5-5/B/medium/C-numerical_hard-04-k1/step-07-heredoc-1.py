import numpy as np
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
r2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
t2g=[vec({-2:1/(1j*r2),2:-1/(1j*r2)}), vec({-1:-1/r2,1:1/r2}), vec({-1:1/(1j*r2),1:1/(1j*r2)})]
eg=[vec({0:1}), vec({-2:1/r2,2:1/r2})]
M=np.array(t2g+eg)
print(np.round(M.conj()@M.T,6))
