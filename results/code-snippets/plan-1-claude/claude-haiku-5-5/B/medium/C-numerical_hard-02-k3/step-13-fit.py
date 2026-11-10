
from scipy.optimize import brentq
def levels_at(x):
    L=trip_levels(x); e0=L[0][0]
    return [(v-e0,dg,c) for v,dg,c in L]
names={}
results=[]
for x in np.arange(2.4,5.0,0.002):
    L=levels_at(x)
    ex=[(v,dg,c) for v,dg,c in L[1:8]]
    for combo in itertools.combinations(range(len(ex)),3):
        Es=np.array([ex[i][0] for i in combo])
        # obs = B*Es  -> fit B by least squares, residual
        B=np.dot(Es,obs)/np.dot(Es,Es)
        res=np.sqrt(np.mean((B*Es-obs)**2))
        results.append((res,round(x,3),round(B,2),[ (ex[i][1],round(ex[i][2],1)) for i in combo]))
results.sort(key=lambda r:r[0])
for r in results[:10]: print(r)
