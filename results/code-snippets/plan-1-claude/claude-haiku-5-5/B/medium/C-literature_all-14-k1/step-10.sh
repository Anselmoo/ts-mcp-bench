
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > sym2.py
import numpy as np
from scipy.linalg import expm
import d7
from sym import rot_matrix
from math import pi
def Rz(phi):
    return np.array([[np.cos(phi),-np.sin(phi),0],[np.sin(phi),np.cos(phi),0],[0,0,1.]])
h=1e-4
K = (rot_matrix(Rz(h)) - rot_matrix(Rz(-h)))/(2*h)   # d/dphi U(phi) at 0
# Check: U(phi) = expm(phi*K0) with K0 generator; K0 = K at phi=0
K10 = np.kron(K, np.eye(2))
G = sum(K10[p,q]*d7.cd[p]@d7.c[q] for p in range(10) for q in range(10) if abs(K10[p,q])>1e-12)
Gs = G[d7.idx][:,d7.idx].toarray()
Gam = expm(Gs*pi/2)
# sanity: Gam^4 should be identity
print("C4^4=1:", np.allclose(np.linalg.matrix_power(Gam,4),np.eye(len(Gam)),atol=1e-6))
np.save('Gam.npy', Gam)
EOF
python3 sym2.py 2>&1 | tail -3
sed -i 's/^Gam = .*//' sym.py; sed -i 's/^Gs = Gmat.*//' sym.py; sed -i 's/^Gmat = .*//' sym.py
cat << 'EOF' > lab.py
import numpy as np
import d7
Gam = np.load('Gam.npy')
def labels(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    Hm = sum(Dq*d7.fieldDq[o]*d7.ONEs[o] for o in range(5)) + d7.Ts[0] + F2*d7.Ts[1] + F4*d7.Ts[2]
    s2,Uq = np.linalg.eigh(d7.S2s)
    out=[]
    for S in (1.5,0.5):
        sel = np.abs(s2-S*(S+1))<1e-6
        Us = Uq[:,sel]
        e,V = np.linalg.eigh(Us.T@Hm@Us)
        Gm = Us.T@Gam@Us
        i=0
        while i<len(e):
            j=i
            while j+1<len(e) and abs(e[j+1]-e[i])<1e-6: j+=1
            Vb = V[:,i:j+1]
            chi = np.trace(Vb.T@Gm@Vb)
            out.append((S, e[i], j-i+1, round(chi.real,3)))
            i=j+1
    return out
if __name__=="__main__":
    for S,e,m,chi in labels(1000.,1000.,4000.):
        print(S, round(e,1), m, chi)
EOF
python3 lab.py