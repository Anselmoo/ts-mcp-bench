
cd <SANDBOX_TMP>/d7 && cat << 'EOF' > cross.py
from d7 import *
from scipy.optimize import brentq
B,C=922.,4156.
def spin_ops(states,sidx):
    D=len(states)
    Sp=np.zeros((D,D))
    for st in states:
        for m in ms:
            up=so.index((m,1)); dn=so.index((m,-1))
            sg,new=apply_ops([('a',dn),('c',up)],st)  # c_up^dag c_dn
            if new is not None: Sp[sidx[new],sidx[st]]+=sg
    Sz=np.array([0.5*(sum(1 for i in st if so[i][1]==1)-sum(1 for i in st if so[i][1]==-1)) for st in states])
    S2=Sp.T@Sp+np.diag(Sz*(Sz+1))  # S- S+ = (S+)^T S+ ; S^2 = S-S+ + Sz^2+Sz? (S^2 = S-S+ + Sz(Sz+1)) 
    return S2
def levels(Dq):
    H,states,sidx=build_H(Dq,B,C)
    S2=spin_ops(states,sidx)
    # diagonalize H in S^2 sectors
    w,v=np.linalg.eigh(S2)
    out={}
    for S in (1.5,0.5):
        P=v[:,np.abs(w-S*(S+1))<1e-6]
        e=np.linalg.eigvalsh(P.conj().T@H@P)
        out[S]=e.min()
    return out
if __name__=="__main__":
    H,states,sidx=build_H(0,B,C)
    S2=spin_ops(states,sidx)
    print("S2 eig:",np.unique(np.round(np.linalg.eigvalsh(S2),3)))
    print("free ion levels (Dq=0) lowest by S:")
    print(levels(0.0))
    for Dq in [0,500,1000,1500,2000,2500,3000]:
        print(Dq,levels(Dq))
EOF
python3 cross.py