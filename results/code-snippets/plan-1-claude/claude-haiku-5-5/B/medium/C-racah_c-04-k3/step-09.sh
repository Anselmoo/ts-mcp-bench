cat > fit.py << 'EOF'
import d3, numpy as np
from scipy.optimize import least_squares
S2=d3.spin2().real
def levels(Dq,B,Cc):
    H=d3.build_H(Dq,B,Cc).real if False else d3.build_H(Dq,B,Cc)
    H=np.array(H)
    w,v=np.linalg.eigh(H)
    s2=np.einsum('ia,ij,ja->a',v.conj(),S2,v).real
    # project per spin sector
    out={}
    for S,lab in [(3.75,'Q'),(0.75,'D')]:
        sel=np.abs(s2-S)<1e-6
        ev=np.linalg.eigvalsh(H)  # placeholder
        Hs=v[:,sel]
        M=Hs.conj().T@H@Hs
        out[lab]=np.linalg.eigvalsh(M)
    return out
def energies(Dq,B,Cc):
    L=levels(Dq,B,Cc)
    q=np.unique(np.round(L['Q'],2)); d=np.unique(np.round(L['D'],2))
    return q,L['D']
if __name__=="__main__":
    q,_=energies(1743,780,3500)
    print("quartet levels", q)
EOF
python3 fit.py