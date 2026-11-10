cd <SANDBOX_TMP>/ts && cat > run4.py << 'EOF'
from run3 import *
import numpy as np
for dq in [0.0, 0.5,1.0,1.5,2.0,2.5,3.0,3.5,4.0]:
    sp = block_spectrum(dq if dq>0 else 1e-9)
    allv=[]
    for key,levs in sp.items():
        for k,(e,L) in enumerate(levs):
            allv.append((e,key,k,np.round(L,2).tolist()))
    allv.sort(key=lambda t:t[0])
    e0 = allv[0][0]
    print(f"Dq={dq}")
    for e,key,k,L in allv[:9]:
        print(f"   {key[0]}{key[1]} idx{k}  E={e-e0:.4f}  L2={L}")
EOF
python3 run4.py 2>&1 | grep -v block