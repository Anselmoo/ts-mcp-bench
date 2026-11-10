mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq, fsolve
l=2; ms=list(range(-2,3)); n=5
def tensor(k,q,m1,m3):  # <l m1|C^k_q|l m3>
    if abs(m1-m3)!=q and False: pass
    if m1-m3!=q: return 0.0  # convention: m1 = m3+q
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m1)*float(wigner_3j(l,k,l,-m1,q,m3))*red
def cmat(k,q):
    return np.array([[tensor(k,q,m1,m3) for m3 in ms] for m1 in ms])
# one-electron cubic field: V = C4_0 + sqrt(5/14)(C4_4+C4_-4) (real-combination form)
def cf_op(k,q):
    return cmat(k,q)
V = cmat(4,0) + np.sqrt(5/14)*(cmat(4,4)+cmat(4,-4))
V=V.astype(complex)
ev=np.linalg.eigvalsh(V); 
print("V eig",np.round(ev,4))
ueg=max(ev,key=lambda x:abs(x)) 
# identify: eg doublet, t2g triplet
vals,counts=np.unique(np.round(ev,6),return_counts=True); print(vals,counts)
EOF
cd /w && python3 ts.py