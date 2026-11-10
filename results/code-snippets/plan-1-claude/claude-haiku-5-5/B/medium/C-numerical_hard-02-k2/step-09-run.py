import numpy as np
from d4 import *
Hfree = build({0:0.0,2:1.0,4:0.625}, np.zeros((5,5)))
H=Hfree.toarray()[np.ix_(sel,sel)]; S2s=S2.toarray()[np.ix_(sel,sel)]
e,v=np.linalg.eigh(H+1e3*S2s)
for i in range(len(e)):
    s2=v[:,i]@S2s@v[:,i]
    if abs(s2-2)<1e-3 : print("triplet", round(e[i],4), round(s2,3))
print("ok")
