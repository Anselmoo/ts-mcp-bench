cd <SANDBOX_TMP> && cat << 'EOF' > run4.py
import sys; sys.path.insert(0,'<SANDBOX_TMP>')
from run2 import doublets
import numpy as np
from scipy.optimize import brentq
obs=np.array([22640,22930,25080.])
def levs(x,B): 
    E=doublets(x,B=B)
    return E-E[0]
# Fit x and B with B scaling: energies are linear in B at fixed x
def model(x):
    L=levs(x,1000.0)/1000.0   # per unit B
    return L
best=None
for x in np.arange(2.8,3.4,0.01):
    L=model(x)
    # lowest three excited levels L[1],L[2],L[3]; B from matching 22640 to L[1]... compute residual for ratio
    for ia,ib,ic in [(1,2,3)]:
        Bfit = obs/np.array([L[ia],L[ib],L[ic]])
        r = np.std(Bfit)/np.mean(Bfit)
        if best is None or r<best[0]: best=(r,x,Bfit)
    print(round(x,2), np.round(L[1:5],3), round(r,4))
print("best",best)
EOF
python3 run4.py 2>&1 | grep -v "^11 \|cwd\|unique\|^ *[0-9]*\.\?[0-9]* *[0-9]*\.\?\]\?$" | tail -50