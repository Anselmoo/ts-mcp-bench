cat << 'EOF' > fit3.py
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
    q=np.sort(E[np.abs(S-3.75)<1e-3])
    vals=[]
    for e in q:
        if not vals or abs(e-vals[-1])>1e-6: vals.append(e)
    return np.array(vals)
def res(p):
    v=qlev(*p)
    if len(v)<4: return np.ones(3)*1e6
    return (v[1:4]-v[0])-obs
best=None
for Dq0 in [500,900,1200]:
  for F20 in [600,1000,1500]:
    for F40 in [40,70,100]:
        r=least_squares(res,[Dq0,F20,F40],xtol=1e-14,ftol=1e-14,gtol=1e-14)
        if best is None or r.cost<best.cost: best=r
Dq,F2,F4=best.x
print("fit",best.x,"resid",best.fun)
print("F4/F2",F4/F2,"B=(9F2-5F4)/441=",(9*F2-5*F4)/441)
v=qlev(*best.x); print("levels rel",v-v[0])
EOF
timeout 500 python3 fit3.py