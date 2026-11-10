cd $TMPDIR && python3 - << 'EOF'
import numpy as np
from d5 import levels
from scipy.optimize import least_squares
from collections import Counter
obs=np.array([22640,22930,25080])
def lv(Dq,B):
    d,a=levels(Dq,B,4.6*B)
    u=sorted(Counter(np.round(np.array(d)-min(a),2)).items())
    return u
def res(x):
    u=lv(*x); return np.array([e for e,_ in u[1:4]])-obs
for g in [(2500,500),(3000,300),(2200,700)]:
    r=least_squares(res,g,diff_step=1e-3)
    print(r.x, r.fun, lv(*r.x)[:6])
EOF