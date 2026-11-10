cat > ident.py << 'EOF'
import numpy as np
from fit import levels, Hcf,H2,H4,basis,sec
from scipy.optimize import least_squares
d=np.load('d7mats.npz'); basis=d['basis']
nup=np.array([sum(1 for o in s if o%2==0) for s in basis])
def Hfull(Dq,B,C):
    F2=49*B+5*C; F4=12.6*C
    return Dq*Hcf+F2*H2+F4*H4
# orbital m for index 2*i+s : m = -2+i
mocc=np.array([sum((o//2)-2 for o in s) for s in basis])
R=np.exp(-1j*np.pi/2*mocc)
def doublet_levels(Dq,B,C):
    H=Hfull(Dq,B,C)
    sub=sec[1]
    Hs=H[np.ix_(sub,sub)]
    w,v=np.linalg.eigh(Hs)
    q=np.linalg.eigvalsh(H[np.ix_(sec[3],sec[3])])
    # identify quartet-level removal
    dlist=list(w)
    for x in q:
        i=int(np.argmin([abs(y-x) for y in dlist])); dlist.pop(i)
    # group doublet eigenvalues with spatial character via C4 trace
    out=[]
    # rebuild eigenvectors for doublets: take all Sz=1/2 eigvecs, remove those belonging to quartets (by matching energies)
    used=set(); res=[]
    qs=sorted(q)
    keep=[]
    for i,x in enumerate(w):
        # check if matches quartet energy
        j=np.argmin([abs(x-y) for y in q])
        if abs(x-q[j])<1e-6*max(1,abs(x)) and j not in used:
            used.add(j); continue
        keep.append(i)
    Vd=v[:,keep]; ed=w[keep]
    Rs=R[sub]
    # group by energy
    groups=[]
    i=0
    while i<len(ed):
        j=i
        while j+1<len(ed) and abs(ed[j+1]-ed[i])<1e-3: j+=1
        P=Vd[:,i:j+1]
        M=P.conj().T@(Rs[:,None]*P)
        tr=np.trace(M).real
        groups.append((ed[i],j-i+1,round(tr,3)))
        i=j+1
    return np.sort(q), groups
if __name__=="__main__":
    q,g=doublet_levels(600,800,3000)
    for x in g: print(x)
EOF
python3 ident.py