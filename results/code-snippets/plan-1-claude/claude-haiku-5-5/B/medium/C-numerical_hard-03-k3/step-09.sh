cd <SANDBOX_TMP> && cat << 'EOF' > run2.py
import sys; sys.path.insert(0,'<SANDBOX_TMP>')
from d5calc import *
def doublets(x,B=1000.0,C=4.6):
    H=build(x*B,B,C*B)
    w,v=np.linalg.eigh(H+1e5*S2)
    S2v=np.einsum('ia,ij,ja->a',v,S2,v)
    sel=np.abs(S2v-0.75)<1e-3
    vs=v[:,sel]
    Hs=vs.T@H@vs
    return np.unique(np.round(np.linalg.eigvalsh(Hs),6))
E=doublets(0.0)
print(len(E), E[:20]-E[0])
EOF
python3 run2.py