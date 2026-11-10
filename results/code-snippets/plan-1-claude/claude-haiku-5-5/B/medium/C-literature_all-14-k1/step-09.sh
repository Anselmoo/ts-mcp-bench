
cd /tmp/tsbench-run-711ytt10/w && cat << 'EOF' > sym.py
import numpy as np
from scipy.linalg import logm, expm
import d7
from run2 import levels
from math import pi
# C4 rotation about z by 90 deg acting on functions: (R f)(r) = f(R^-1 r)
def rot_matrix(Rm):
    # points on grid rotated
    P = np.stack([d7.X.ravel(), d7.Y.ravel(), d7.Z.ravel()])
    Q = Rm.T @ P   # R^-1 applied to points (R^-1 = R^T)
    th = np.arccos(np.clip(Q[2],-1,1)); ph = np.arctan2(Q[1],Q[0])
    X,Y,Z = Q
    fr = [np.sqrt(15/(4*pi))*X*Y, np.sqrt(15/(4*pi))*Y*Z, np.sqrt(15/(4*pi))*X*Z,
          np.sqrt(5/(16*pi))*(3*Z**2-1), np.sqrt(15/(16*pi))*(X**2-Y**2)]
    W = d7.W.ravel()
    U = np.zeros((5,5))
    for a in range(5):
        for b in range(5):
            U[a,b] = np.sum(W*fr[a]*d7.f[b].ravel())
    return U
c4 = np.array([[0,-1,0],[1,0,0],[0,0,1.]])
U = rot_matrix(c4)
print(np.round(U,6))
# check orthogonal
print(np.allclose(U@U.T,np.eye(5),atol=1e-6))
W10 = np.kron(U, np.eye(2))  # orbital index*2+spin ordering -> orbital outer? need check
# our spin-orbital index p=2*orb+s  => kron(U,I2) is correct
L = logm(W10).real
G = np.zeros((10,10))
Gmat = sum(L[p,q]*d7.cd[p]@d7.c[q] for p in range(10) for q in range(10) if abs(L[p,q])>1e-12)
Gs = Gmat[d7.idx][:,d7.idx].toarray()
Gam = expm(Gs)
np.save('Gam.npy', Gam)
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
        # group degenerate levels
        i=0
        while i<len(e):
            j=i
            while j+1<len(e) and abs(e[j+1]-e[i])<1e-6: j+=1
            Vb = V[:,i:j+1]
            chi = np.trace(Vb.T@Gm@Vb)  # trace of C4 in this level
            out.append((S, e[i], j-i+1, round(chi,3)))
            i=j+1
    return out
if __name__=="__main__":
    E0 = None
    for S,e,m,chi in labels(1000.,1000.,4000.):
        print(S, round(e,1), m, chi)
EOF
sed -i 's/^ONEs = .*/&\nW = None/' d7.py
python3 - << 'EOF'
import re
src=open('/tmp/tsbench-run-711ytt10/w/d7.py').read()
src=src.replace("W = None\n","")
# add grid weights for rotation use
src+="\nWG = W\n"
open('/tmp/tsbench-run-711ytt10/w/d7.py','w').write(src)
EOF
sed -i 's/W = d7.W.ravel()/W = d7.WG.ravel()/' sym.py
python3 sym.py