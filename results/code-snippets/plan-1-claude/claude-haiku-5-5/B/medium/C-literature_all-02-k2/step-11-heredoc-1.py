import numpy as np
from sympy.physics.wigner import gaunt
ms=range(-2,3)
S=0; S2=0
for a in ms:
  for b in ms:
    for q in range(-2,3):
      if -a+b-q==0:
        S+=float(gaunt(2,2,2,-a,b,-q))**2
print("sum G^2 =",S, " expected", 125/(4*np.pi)*2/35)
