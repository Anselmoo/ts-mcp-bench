import numpy as np
from scan import triplet_levels
obs = np.array([18850,19750,20560.])
best=[]
xs = np.arange(0.5,4.0,0.005)
for x in xs:
    lev = triplet_levels(x)
    E = np.array([a-lev[0][0] for a,m in lev])
    deg = [m for a,m in lev]
    # ignore the ground-level group itself (E=0) 
    idx = [i for i in range(1,len(E))]
    # choose 3 levels i<j<k (ordered) for bands
    for i in idx:
        for j in idx:
            for k in idx:
                if not (i<j<k): continue
                # fit B: nu_n = B*E_n ; least squares; residual
                f = np.array([E[i],E[j],E[k]])
                B = (f@obs)/(f@f)
                res = np.sqrt(np.mean((B*f-obs)**2))
                best.append((res,x,B,(i,j,k),tuple(np.round(f,4)),tuple(deg[n] for n in (i,j,k))))
best.sort(key=lambda t:t[0])
for b in best[:15]: print(b)
