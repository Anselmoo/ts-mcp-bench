from d3 import *
import numpy as np
S2m=S2(); L2m=L2()
res=[]
for F2,F4 in [(1.0,0.0),(0.0,1.0),(1.0,1.0)]:
    F={0:0.0,2:F2,4:F4}
    H=build(F)
    # project: diagonalize H + mu*S2 + nu*L2 to label (S,L)
    M=H+1e3*S2m+1e-3*L2m
    w,v=np.linalg.eigh(M)
    out=[]
    for i in range(120):
        s2=v[:,i]@S2m@v[:,i]; l2=v[:,i]@L2m@v[:,i]; e=v[:,i]@H@v[:,i]
        out.append((round(s2,3),round(l2,3),round(e,6)))
    import collections
    d=collections.Counter(out)
    print(F2,F4)
    for k in sorted(d): print(k,d[k])
