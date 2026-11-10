python3 -c "
import numpy as np
from sympy.physics.wigner import gaunt
from math import sqrt
ms=list(range(-2,3))
gnt=lambda *a: float(gaunt(*a))
W=np.zeros((5,5))
for i,m in enumerate(ms):
  for j,mp in enumerate(ms):
    for q,a in ((0,1.0),(4,sqrt(5/14)),(-4,sqrt(5/14))):
      if (-m+q)!=mp: continue
      W[i,j]+=a*((-1)**m)*gnt(2,4,2,-m,q,mp)
print(np.round(W,4)); print(np.linalg.eigvalsh(W))
"