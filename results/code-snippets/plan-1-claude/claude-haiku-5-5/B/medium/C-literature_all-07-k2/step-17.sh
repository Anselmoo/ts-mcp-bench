
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > fit2.py
import numpy as np
from sym import levels_sym
from scipy.optimize import least_squares
def getT(Dq,B,C):
    rows=levels_sym(Dq,B,C)
    T1=[r[0] for r in rows if r[1]==3 and r[2]==1 and r[3]==-1 and r[0]>1e-6]
    T2=[r[0] for r in rows if r[1]==3 and r[2]==-1 and r[3]==-1 and r[0]>1e-6]
    E=[r[0] for r in rows if r[1]==2 and r[0]>1e-6]
    return T1[0],T2[0],E[0] if E else None
def res(x):
    Dq,B=x; C=4600-2*B
    t1,t2,e=getT(Dq,B,C)
    return [t1-19240, t2-21890]
for g in [(800,900),(900,850),(700,1000)]:
    s=least_squares(res,g,diff_step=1e-4,x_scale=[100,100])
    Dq,B=s.x; C=4600-2*B
    print(s.x, C, s.fun, getT(Dq,B,C), flush=True)
EOF
timeout 900 python3 fit2.py
