import numpy as np
from scan import levels
obs=np.array([29360,29620,31640.])
for r in [3.5,4.0,4.5,5.0,5.5,6.0]:
    L=levels(r,1.0)
    ex=[v for v,m in L[1:]]
    v=np.array(ex[:3]); B=np.dot(v,obs)/np.dot(v,v)
    print(r, np.round(ex[:5],3), np.round(v*B), round(B,1))
