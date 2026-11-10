cat > fit.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
M=np.load('mats.npz'); H2,H4,HCF=M['H2'],M['H4'],M['HCF']
ms=[-2,-1,0,1,2]
dets_up=None
import itertools
so=[(m,s) for s in (+1,-1) for m in ms]
dets=[frozenset(c) for c in itertools.combinations(range(10),3)]
up=[i for i,d in enumerate(dets) if all(so[k][1]==+1 for k in d)]
mid=[i for i,d in enumerate(dets) if sum(so[k][1] for k in d)==1]
def levels(F2,F4,Dq):
    H=F2*H2+F4*H4+Dq*HCF
    q=np.linalg.eigvalsh(H[np.ix_(up,up)])
    dd=np.linalg.eigvalsh(H[np.ix_(mid,mid)])
    rem=list(dd)
    for e in q:
        j=int(np.argmin([abs(r-e) for r in rem])); rem.pop(j)
    return np.sort(q), np.sort(np.array(rem))
def group(v,tol=0.5):
    out=[]
    for e in v:
        if out and abs(e-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([e,1])
    return out
# check free ion Racah: F4=0, F2=1 -> B=1/441
q,dbl=levels(1.0,0.0,0.0)
print("free ion quartets (F2=1):",[(round(e,4),n) for e,n in group(q)])
print("doublets:",[(round(e,4),n) for e,n in group(dbl)])
q,dbl=levels(0.0,1.0,0.0)
print("F4=1 quartets:",[(round(e,4),n) for e,n in group(q)])
EOF
python3 fit.py