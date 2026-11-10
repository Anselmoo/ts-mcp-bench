
cd /tmp/tsbench-run-de_x16pn && cat << 'EOF' > fit.py
import numpy as np, pickle
from scipy.optimize import fsolve
H1,Hk,states,Sp=pickle.load(open('mats.pkl','rb'))
Sz=np.array([sum((1 if (x%2==0) else -1) for x in st)/2 for st in states])
# so index: x = 2*mi + (0 for s=+1,1 for s=-1)
Sz=np.array([sum((1 if x%2==0 else -1) for x in st)/2 for st in states])
S2=Sp.conj().T@Sp+np.diag(Sz*Sz+Sz)
S2=np.real_if_close(S2)
def levels(B,Dq,C=None):
    C=4.5*B if C is None else C
    F4=7*C/5; F2=49*B+7*C-0  # F2=49B+5F4
    F2=49*B+5*F4
    H=H1*1.0+F2*Hk[2]+F4*Hk[4]
    # restrict to Dq scaling: H1 was built with Dq=1 (e=-6,t2=+4)
    H=H1*Dq+F2*Hk[2]+F4*Hk[4]
    # triplet, Sz=1 subspace
    sel=[i for i,st in enumerate(states) if Sz[i]==1]
    # S2 eigen: restrict to triplets
    w,v=np.linalg.eigh(S2)
    T=v[:,np.abs(w-2)<1e-6]
    Ht=T.conj().T@H@T
    Ht=(Ht+Ht.conj().T)/2
    # Sz=1 subspace within triplets
    Tz=np.array([Sz[i] for i in range(len(states))])
    ev=np.linalg.eigvalsh(Ht)
    return ev
# check free ion (Dq=0)
ev=levels(1000,0)
print(np.round(np.unique(np.round(ev,3)),1))
EOF
python3 fit.py