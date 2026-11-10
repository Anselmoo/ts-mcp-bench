cat << 'EOF' > fit2.py
from run import *
from scipy.optimize import least_squares
import collections
obs=np.array([9460,20160,21160.])
def qlev(Dq,F2,F4):
    w,S=levels(Dq,0.0,F2,F4)
    q=np.sort(w[np.abs(S-3.75)<1e-3])
    vals=[]
    for e in q:
        if not vals or abs(e-vals[-1])>1e-7: vals.append(e)
    return np.array(vals)  # ascending, first = ground
def resid(p):
    Dq,F2,F4=p
    v=qlev(Dq,F2,F4)
    return (v[1:4]-v[0]) - obs/1.0
# scale: work in cm-1 directly; parameters are cm-1 for Dq,F2,F4
def res_scaled(p):
    Dq,F2,F4=p
    v=qlev(Dq,F2,F4)
    return (v[1:4]-v[0])-obs
best=None
for Dq0 in [800,1000]:
  for F20 in [800,1200,1600]:
    for F40 in [40,60,80]:
        try:
            r=least_squares(res_scaled,[Dq0,F20,F40],xtol=1e-12,ftol=1e-12,gtol=1e-12)
        except Exception as e:
            continue
        if best is None or r.cost<best.cost: best=r
print(best.x, best.fun, best.cost)
Dq,F2,F4=best.x
B=(9*F2-5*F4)/441; C=35*F4/441*0+ (F4*35/441*0)
print("Dq",Dq,"B",B,"F4/F2",F4/F2)
print("levels",qlev(Dq,F2,F4)-qlev(Dq,F2,F4)[0])
EOF
python3 fit2.py