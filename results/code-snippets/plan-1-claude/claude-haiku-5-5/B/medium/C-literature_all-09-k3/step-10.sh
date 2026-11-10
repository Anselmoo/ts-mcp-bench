cat > spec.py << 'EOF'
from ligf import *
import numpy as np
def quartet_levels(Dq,B,C):
    w,ss=build(Dq,B,C)
    S=np.round((-1+np.sqrt(1+4*ss))/2*2)/2
    g0=w[np.isclose(S,2.5)].min()
    q=w[np.isclose(S,1.5)]-g0
    q=np.sort(q)
    # cluster
    lev=[]
    for x in q:
        if lev and abs(x-lev[-1][0])<0.05: lev[-1][1]+=1
        else: lev.append([x,1])
    return np.array(lev)
EOF
python3 -c "
from spec import *
for Dq in [0,500,740,1000]:
    print('Dq',Dq)
    print(np.round(quartet_levels(Dq,860,3500),2).tolist())
"