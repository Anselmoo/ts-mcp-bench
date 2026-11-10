
cd /tmp/tsbench-run-ub74fb61 && cat << 'EOF' > sym.py
import numpy as np
from d5 import *
from fit import sub, allup
def levels_sym(Dq,B,C,tol=1e-5):
    F=(0.0, 49*B+7*C, 441*C/35)
    H=build(F,Dq).real
    Esx=H[allup,allup]
    Hs=H[np.ix_(sub,sub)]
    w,v=np.linalg.eigh(Hs)
    # phases for C4z (theta=pi/2) and C2z (theta=pi)
    subdets=[dets[i] for i in sub]
    def phase(theta):
        return np.array([np.exp(-1j*sum(orbs[x][0] for x in d)*theta) for d in subdets])
    p4=phase(np.pi/2); p2=phase(np.pi)
    out=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<tol: j+=1
        V=v[:,i:j+1]
        t4=np.trace(V.conj().T@(p4[:,None]*V)).real
        t2=np.trace(V.conj().T@(p2[:,None]*V)).real
        out.append((w[i]-Esx, j-i+1, round(t4,3), round(t2,3)))
        i=j+1
    return out
if __name__=="__main__":
    import sys
    Dq,B,C=map(float,sys.argv[1:4])
    for row in levels_sym(Dq,B,C):
        if abs(row[0])>1e-6: print(np.round(row[0],1), row[1], row[2], row[3])
EOF
timeout 900 python3 sym.py 800 800 3200
