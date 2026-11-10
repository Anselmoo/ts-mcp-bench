
cd /tmp/tsbench-run-de_x16pn && cat << 'EOF' > dbg.py
import numpy as np, pickle
H1,Hk,states,Sp=pickle.load(open('mats.pkl','rb'))
Sz=np.array([sum((1 if x%2==0 else -1) for x in st)/2 for st in states])
S2=Sp.conj().T@Sp+np.diag(Sz*Sz+Sz)
print(np.unique(np.round(np.linalg.eigvalsh(S2),6),return_counts=True))
print(np.unique(np.round(np.linalg.eigvalsh(Hk[2]),4),return_counts=True))
print(np.unique(np.round(np.linalg.eigvalsh(H1),4),return_counts=True))
EOF
python3 dbg.py