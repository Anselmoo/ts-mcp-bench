import numpy as np
from scipy.optimize import least_squares
from fit import levels
obs=np.array([9180,19550,20320.])
def spinallowed(p, S0):
    Dq,B,C=p
    w,S=levels(Dq,B,C)
    g=w[0]
    gs=S[0]
    out=[]
    for e,s in zip(w,S):
        if abs(s-gs)<1e-6 and e-g>1e-6:
            if not out or abs(e-g-out[-1])>1e-3: out.append(e-g)
    return np.array(out), gs
import sys
best=[]
for start in [(900,800,3500),(1200,600,3000),(1500,900,4000),(800,1000,4500),(1800,700,3000)]:
    def res(p):
        tr,gs=spinallowed(p,None)
        if len(tr)<3: return np.ones(3)*1e5
        return tr[:3]-obs
    r=least_squares(res,start,diff_step=1e-3,max_nfev=400)
    tr,gs=spinallowed(r.x,None)
    print(np.round(r.x,1), 'gs S=',gs, 'trans', np.round(tr[:5]), 'cost',round(r.cost,2))
