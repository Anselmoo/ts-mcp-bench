
cd /tmp/tsbench-run-de_x16pn && cat << 'EOF' > fit2.py
import numpy as np, pickle
from scipy.optimize import brentq
H1,Hk,states,Sp=pickle.load(open('mats.pkl','rb'))
Sz=np.array([sum((1 if x%2==0 else -1) for x in st)/2 for st in states])
S2=Sp.conj().T@Sp+np.diag(Sz*Sz+Sz)
w,v=np.linalg.eigh(S2); T=v[:,np.abs(w-2)<1e-6]
P1=T.conj().T@H1@T; P2=T.conj().T@Hk[2]@T; P4=T.conj().T@Hk[4]@T
def levels(B,Dq,C=None):
    C=4.5*B if C is None else C
    F4=12.6*C; F2=49*B+5*F4/9
    H=Dq*P1 - (F2*P2+F4*P4)
    ev=np.linalg.eigvalsh((H+H.conj().T)/2)
    vals=[];
    for e in ev:
        if vals and abs(e-vals[-1][0])<1e-3: vals[-1][1]+=1
        else: vals.append([e,1])
    return vals
for B,Dq in [(1000,0)]:
    print(levels(B,Dq))
EOF
python3 fit2.py