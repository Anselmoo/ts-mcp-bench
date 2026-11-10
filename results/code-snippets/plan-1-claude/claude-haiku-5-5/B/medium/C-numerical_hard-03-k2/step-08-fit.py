
obs=np.array([22640,22930,25080.])
from itertools import combinations
def excited(Dq,B):
    e=levels(Dq,B)
    d=distinct(e,tol=1e-6*max(1,abs(e).max()))
    g=d[0][0]
    return [(v-g,deg) for v,deg in d[1:]]
# scan over ratio x=Dq/B
best=[]
for x in np.linspace(1.0,6.0,501):
    ex=excited(x,1.0)
    # for each triple of excited levels (lowest 6) compute best scale B: energies = B*f_i(x)
    for comb in combinations(range(min(7,len(ex))),3):
        f=np.array([ex[i][0] for i in comb])
        # best B minimizing |B f - obs|^2
        Bs=np.dot(f,obs)/np.dot(f,f)
        res=np.sqrt(np.mean((Bs*f-obs)**2))
        best.append((res,x,comb,Bs,Bs*x))
best.sort()
for b in best[:10]: print(b)
