import numpy as np
from scipy.optimize import least_squares
from fit2 import quartet_rel, triplets, spectrum
def r3(p):
    qr=quartet_rel(p)
    return np.array([qr[1]-6150, qr[2]-12400, qr[3]-16850])
best=None
for Dq0 in [500,600,700,800]:
  for B0 in [600,800,1000]:
    for C0 in [3000,4000,4500]:
        s=least_squares(r3,[Dq0,B0,C0],x_scale=[100,100,500],xtol=1e-12,ftol=1e-12)
        if s.cost<1e-6 and (best is None or s.cost<best.cost): best=s
        
print("quartet-only fit:",best.x if best is not None else None, best.cost if best else None)
if best is not None:
    p=best.x
    q,_=spectrum(p); tr=triplets(p)-q[0]
    print("quartets rel",quartet_rel(p))
    print("triplets rel",np.round(tr,1))
