import numpy as np
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(((-1)**m1)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
for k in (2,4):
  print(k,[[round(ck(k,a,b)*(7 if k==2 else 21),3) for b in ms] for a in ms])
