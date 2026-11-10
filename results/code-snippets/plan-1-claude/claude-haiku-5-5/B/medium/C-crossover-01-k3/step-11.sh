python3 - << 'EOF'
import numpy as np
exec(open('d4.py').read().split("for Dq in [0,500")[0])
def lo(Dq,S):
    H=Hee+np.diag(Dq*Hcf); P=S2-S*(S+1)*np.eye(nd)
    return np.linalg.eigvalsh(H+1e6*P@P)[0]
for D in [1200,1400,1500,1565,1600,1700,1800]:
    print(D, round(lo(D,0)+6*D,1), round(lo(D,1)+6*D,1))
EOF