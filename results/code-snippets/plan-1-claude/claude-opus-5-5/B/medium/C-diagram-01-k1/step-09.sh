export MPLCONFIGDIR=$PWD/.mpl; cat > run2.py <<'EOF'
from ts import *
import numpy as np, json
def lab(m,d,c):
    sym={1:('A1' if c>0 else 'A2'),2:'E',3:('T1' if c>0 else 'T2')}[d]
    return f"{m}{sym}g"
def get(dq):
    L=levels(dq); e0=L[0][0]
    return [(e-e0,lab(m,d,c)) for e,m,d,c,n in L]
for dq in [1e-6,1e-5]:
    print(dq,[(round(e,6),l) for e,l in get(dq)[:9]])
res=[]
for k in range(9):
    dq=0.5*k
    L=get(dq if dq>0 else 1e-7)
    if dq==0: L=[(round(e,3),l) for e,l in L]  # snap
    ex=get(dq)  # actual energies
    res.append((dq,L[:8]))
    print(dq,[(round(e,4),l) for e,l in L[:8]])
EOF
python3 run2.py