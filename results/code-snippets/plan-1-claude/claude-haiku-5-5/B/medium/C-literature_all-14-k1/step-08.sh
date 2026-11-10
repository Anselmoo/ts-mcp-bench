
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > fit.py
import numpy as np
from scipy.optimize import least_squares
import d7
from run2 import levels
def uniq(e):
    out=[]
    for v in np.sort(e):
        if out and abs(v-out[-1][0])<1e-6: out[-1][1]+=1
        else: out.append([v,1])
    return out
def terms(Dq,B,C):
    L=levels(Dq,B,C)
    q=uniq(L[1.5]); d=uniq(L[0.5])
    return q,d
q,d = terms(1000.,1000.,4000.)
print("quartets", [(round(a-q[0][0],1),m) for a,m in q])
print("doublets", [(round(a-q[0][0],1),m) for a,m in d])
EOF
python3 fit.py