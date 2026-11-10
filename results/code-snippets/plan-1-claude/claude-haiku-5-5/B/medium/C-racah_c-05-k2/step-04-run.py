from d3 import *
import collections
S2m=S2(); L2m=L2()
for F2,F4 in [(1.0,0.0),(0.0,1.0)]:
    H=build({0:0.0,2:F2,4:F4})
    M=H+1e3*S2m+1e-3*L2m
    w,v=np.linalg.eigh(M)
    out=[]
    for i in range(120):
        x=v[:,i]
        out.append((round(x@S2m@x,2),round(x@L2m@x,2),round(x@H@x,4)))
    d=collections.Counter([(a,b) for a,b,_ in out])
    print("F2,F4=",F2,F4)
    for k in sorted(d):
        es=sorted(set(round(e,4) for a,b,e in out if (a,b)==k))
        print(k,d[k],es)
