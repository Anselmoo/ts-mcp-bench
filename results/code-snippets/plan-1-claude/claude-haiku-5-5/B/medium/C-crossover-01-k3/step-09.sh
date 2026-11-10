python3 - << 'EOF'
import numpy as np
src=open('d4.py').read()
src=src.split("for Dq in [0,500")[0]
exec(src)
from scipy.optimize import brentq
def lo(Dq,S):
    H=Hee+np.diag(Dq*Hcf); P=S2-S*(S+1)*np.eye(nd)
    return np.linalg.eigvalsh(H+1e6*P@P)[0]
for Dq in [0,1000,2000,2500,3000,3500,4000]:
    print(Dq,[round(lo(Dq,S),1) for S in [0,1,2]])
EOF