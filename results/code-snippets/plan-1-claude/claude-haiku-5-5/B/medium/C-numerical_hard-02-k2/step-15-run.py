import numpy as np, itertools
from d4 import *
B=1.0; C=4.3*B
F4=441*C/35; F2=(441*B+5*F4)/9
F={0:0.0,2:F2,4:F4}
obs=np.array([22900,23730,24580.])
xs=np.arange(2.0,7.0,0.02)
table=[]
for xx in xs:
    lv=levels(4,F,xx*h_unit,1)
    E0=lv[0][0]
    table.append(([e_-E0 for e_,m in lv[1:8]],[m for e_,m in lv[1:8]]))
best=[]
for xi,xx in enumerate(xs):
    tau,deg=table[xi]
    for trip in itertools.combinations(range(6),3):
        t=np.array([tau[i] for i in trip])
        # least squares B: obs ~ B*t
        Bf=np.dot(t,obs)/np.dot(t,t)
        r=np.sqrt(np.mean((Bf*t-obs)**2))
        best.append((r,xx,Bf,trip,tuple(deg[i] for i in trip)))
best.sort()
for b in best[:12]:
    r,xx,Bf,trip,dg=b
    print("rms=%.1f  Dq/B=%.3f  B=%.1f  Dq=%.0f  levels=%s deg=%s"%(r,xx,Bf,xx*Bf,trip,dg))
