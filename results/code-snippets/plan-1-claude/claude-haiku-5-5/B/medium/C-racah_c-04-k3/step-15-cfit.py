import numpy as np, fit
from scipy.optimize import brentq
def lowest_D(Dq,B,C):
    L=fit.levels(Dq,B,C)
    g=L['Q'].min()
    return L['D']-g
for C in [3500,4000,4100,4200]:
    r=np.sort(lowest_D(1743,780.7,C))
    u,cnt=np.unique(np.round(r,0),return_counts=True)
    print(C, list(zip(u[:6],cnt[:6])))
