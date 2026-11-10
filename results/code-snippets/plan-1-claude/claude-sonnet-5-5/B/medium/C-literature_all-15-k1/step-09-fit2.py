from d7 import *
from scipy.optimize import least_squares
def model(p,j):
    Dq,B,C=p; o=lv(Dq,B,C); g=groups(o['q']); e0=g[0][0]
    qs=[x-e0 for x,c in g]
    qe=[x for x,c in g]
    dd=[x-e0 for x,c in groups(o['d']) if min(abs(x-y) for y in qe)>1e-3]
    dd3=[x-e0 for x,c in groups(o['d']) if min(abs(x-y) for y in qe)>1e-3 and c==3]
    return [qs[1],qs[2],qs[3],dd3[j]],dd3
for j in range(2,7):
  best=None
  for st in ([900,800,3000],[900,900,3500],[850,700,3000],[900,1000,4000]):
    try:
        r=least_squares(lambda p: np.array(model(p,j)[0])-[8480,16305,20360,21001],st,x_scale=[100,100,300])
    except Exception as e: continue
    if best is None or r.cost<best.cost: best=r
  print(j,best.x.round(1),best.fun.round(0),[round(x) for x in model(best.x,j)[1]][:9])
