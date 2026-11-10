cat > fit2.py <<'EOF'
import numpy as np
from scipy.optimize import least_squares
H2,H4,HD,S2=np.load('m.npy')
def levels(Dq,B,Cr=4.4):
    Cc=Cr*B; F4=441*Cc/35; F2=49*(B+5*F4/441)
    H=F2*H2+F4*H4+Dq*HD
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-4*max(1,abs(w[i])): j+=1
        P=v[:,i:j]; s=np.linalg.eigvalsh(P.T@S2@P)
        for ss in np.unique(np.round(s,2)):
            n=np.sum(np.round(s,2)==ss)
            out.append((w[i],ss,n))
        i=j
    return out
def show(Dq,B,n=14):
    L=levels(Dq,B); e0=L[0][0]
    for e,s,g in L[:n]: print(round(e-e0),{0.75:'2',3.75:'4',8.75:'6'}.get(s,s),g)
if __name__=='__main__':
    show(3000,600)
EOF
python3 fit2.py