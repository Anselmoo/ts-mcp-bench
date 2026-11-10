import numpy as np, fit
def rel(Dq,B,C):
    L=fit.levels(Dq,B,C)
    g=L['Q'].min()
    return np.sort(L['D']-g), np.unique(np.round(L['D']-g,1),return_counts=True)
for Dq in [0,1743,2500]:
    s,(u,cnt)=rel(Dq,780,3500)
    print("Dq",Dq)
    print(np.round(u[:8]),cnt[:8])
