cd /tmp/tsbench-run-7__jfl5e; cat > an.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
d=np.load('parts.npz'); Hob,H2,H4,S2=d['Hob'],d['H2'],d['H4'],d['S2']
# quartet subspace: eigenvectors of S2 with 15/4
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]; Dd=v[:,np.abs(w-3/4)<1e-6]
print("quartet dim",Q.shape[1],"doublet dim",Dd.shape[1])
def levels(Dq,B,C):
    F2=49*B+7*C; F4=7*C/5
    H=Dq*Hob+F2*H2+F4*H4
    eq=np.linalg.eigvalsh(Q.T@H@Q); ed=np.linalg.eigvalsh(Dd.T@H@Dd)
    return eq,ed
eq,ed=levels(1000,0,0)
print("Dq only quartets",np.round(eq-eq[0],1))
print("doublets",np.round(ed-eq[0],1))
# free ion check B only
eq,ed=levels(0,1,0); print("free ion quartets (B=1)",np.round(eq-eq[0],4))
eq,ed=levels(0,0,1); print("free ion (C=1) quartets",np.round(eq-eq[0],4), "doublets",np.round(ed-eq[0],4))
EOF
python3 an.py