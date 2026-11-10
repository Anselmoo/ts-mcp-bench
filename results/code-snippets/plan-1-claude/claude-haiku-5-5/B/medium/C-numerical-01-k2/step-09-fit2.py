
from scipy.optimize import minimize
def cost(p):
    T=trans(p[0],p[1],p[2]); 
    if len(T)<3: return 1e12
    return float(np.sum((np.array(T[:3])-obs)**2))
best=None
for C0 in [2000,3000,4000]:
    r=minimize(cost,[2230,740,C0],method='Nelder-Mead',options={'xatol':1e-4,'fatol':1e-6,'maxiter':5000})
    print(r.x, r.fun, trans(*r.x)[:3])
    if best is None or r.fun<best.fun: best=r
