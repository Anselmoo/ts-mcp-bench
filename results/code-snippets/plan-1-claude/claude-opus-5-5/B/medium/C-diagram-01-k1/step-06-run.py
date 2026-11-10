from ts import *
for dq in [0,1e-4,0.5]:
    L=levels(dq); e0=L[0][0]
    print(dq,[(round(e-e0,3),m,d,c) for e,m,d,c,n in L[:12]])
