
cd /tmp/tsbench-run-bifa9lgd && cat << 'EOF' > run3.py
import numpy as np, itertools
from run2 import levels
from scipy.optimize import least_squares
obs=np.array([18850,19750,20560.])
def distinct(w):
    out=[]
    for x in w:
        if x<1e-6: continue
        if not out or abs(x-out[-1][0])>1: out.append([x,1])
        else: out[-1][1]+=1
    return out
def tr(Dq,B):
    w=levels(Dq,B); return distinct(w-w[0])
# levels in terms of dimension: compute on grid to find linear behavior; just fit directly
best=[]
for combo in itertools.combinations(range(6),3):
    def res(p):
        Dq,B=p
        d=tr(Dq,B)
        return np.array([d[i][0] for i in combo])-obs
    try:
        r=least_squares(res,[1500,800],bounds=([300,300],[4000,1500]))
        best.append((np.sum(r.fun**2),combo,r.x))
    except Exception as e: pass
best.sort(key=lambda t:t[0])
for b in best[:5]: print(b)
EOF
timeout 600 python3 run3.py 2>&1 | tail -8