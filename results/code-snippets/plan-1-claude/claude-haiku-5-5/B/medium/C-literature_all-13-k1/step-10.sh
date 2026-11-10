python3 -c "
from d7 import *
import numpy as np
for B,C in [(100,0),(0,100),(100,400)]:
    H,S2=build(0,B,C)
    w,v=np.linalg.eigh(H+1e5*S2)
    res={}
    for vec in v.T:
        s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
        if abs(S-1.5)<1e-6:
            res.setdefault(round(vec@H@vec,3),0); res[round(vec@H@vec,3)]+=1
    print(B,C,sorted(res.items()))
"