
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > run2.py
import numpy as np
import d7
def levels(Dq,B,C):
    F2 = 49*B + 7*C; F4 = 63*C/5
    Hm = sum(Dq*d7.fieldDq[o]*d7.ONEs[o] for o in range(5)) + d7.Ts[0] + F2*d7.Ts[1] + F4*d7.Ts[2]
    # block-diagonalize by S: diagonalize S2 then H in each eigenspace
    s2, U = np.linalg.eigh(d7.S2s)
    out={}
    for S in (1.5, 0.5):
        target = S*(S+1)
        sel = np.abs(s2-target)<1e-6
        Us = U[:,sel]
        e = np.linalg.eigvalsh(Us.T@Hm@Us)
        out[S]=np.sort(e)
    return out
if __name__=="__main__":
    L = levels(0,1,0)
    print("quartet:", np.round(L[1.5]-L[1.5][0],1))
    print("doublet:", np.round(L[0.5]-L[1.5][0],1))
    print(len(L[1.5]),len(L[0.5]))
EOF
python3 run2.py