import numpy as np
from math import sqrt
s2=sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
vs={'dxy':vec({2:1/(1j*s2),-2:-1/(1j*s2)}),'dxz':vec({1:-1/s2,-1:1/s2}),'dyz':vec({1:1j/s2,-1:1j/s2}),'dz2':vec({0:1}),'dx2':vec({2:1/s2,-2:1/s2})}
for k,v in vs.items(): print(k, np.round(np.linalg.norm(v),3))
# orthogonality
ks=list(vs)
for i in ks:
    print(i,[round(abs(np.vdot(vs[i],vs[j])),3) for j in ks])
