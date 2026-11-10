cd <SANDBOX_TMP> && cat > fit.py <<'E'
from d7 import *
from scipy.optimize import least_squares
def q(Dq,B):
    w=lv(Dq,B,3000)['q']; g=groups(w); e0=g[0][0]
    return [x-e0 for x,c in g]
def res(p):
    g=q(*p); return [g[1]-8480,g[2]-16305,g[3]-20360]
r=least_squares(res,[900,800],x_scale=[100,100]) if False else None
import numpy as np
# 3 eq 2 unknowns, but 4T1 quartets don't depend on C: least squares
r=least_squares(lambda p: res(p)[:3],[900,800])
print(r.x,r.fun,q(*r.x))
Dq,B=r.x
for C in (2800,3200,3600,4000,4400):
    o=lv(Dq,B,C); e0=o['q'][0]
    print(C,[(round(x-e0)) for x,c in groups(o['d']) if c==3 and abs(x-e0-21000)<4000])
E
python3 fit.py