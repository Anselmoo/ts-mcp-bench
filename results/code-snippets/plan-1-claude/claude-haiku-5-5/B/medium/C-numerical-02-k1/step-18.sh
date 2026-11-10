cd /tmp/tsbench-run-aa74wow9/d7; python3 -c "
import numpy as np
from scipy.optimize import least_squares
d=np.load('mats.npz'); Hd,H2,H4,S2=d['Hd'],d['H2'],d['H4'],d['S2']
obs=np.array([9460,20160,21160.])
def levels(Dq,F2,F4):
    H=Dq*Hd+F2*H2+F4*H4
    w,v=np.linalg.eigh(H+50*S2)
    S=np.real(np.einsum('in,ij,jn->n',v,S2,v))
    E=np.real(np.einsum('in,ij,jn->n',v,H,v))
    return E,S
def qlev(Dq,F2,F4):
    E,S=levels(Dq,F2,F4)
    q=np.sort(E[np.abs(S-3.75)<1e-3]); vals=[]
    for e in q:
        if not vals or abs(e-vals[-1])>1e-6: vals.append(e)
    return np.array(vals)
def res(p):
    v=qlev(*p)
    if len(v)<4: return np.ones(3)*1e5
    return (v[1:4]-v[0])-obs
# scan F4/F2 ratio and solve Dq,F2
for r_ in [0.0,0.3,0.5,0.625]:
    best=None
    for Dq0 in [600,900,1200]:
      for F20 in [30000,60000,90000]:
        rr=least_squares(lambda p: res([p[0],p[1],r_*p[1]]),[Dq0,F20],x_scale=[1000,10000])
        if best is None or rr.cost<best.cost: best=rr
    Dq,F2=best.x; B=(9*F2-5*r_*F2)/441
    print('ratio',r_,'Dq',round(Dq,1),'F2',round(F2,1),'B',round(B,1),'resid',np.round(best.fun,2))
    print('  levels', np.round(qlev(Dq,F2,r_*F2)-qlev(Dq,F2,r_*F2)[0],0))
"