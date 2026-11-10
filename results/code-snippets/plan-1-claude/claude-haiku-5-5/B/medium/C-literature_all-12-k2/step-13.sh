cat > fit2.py << 'EOF'
import numpy as np
from scipy.optimize import least_squares
from fit import levels, sec
d=np.load('d7mats.npz'); Hcf=d['Hcf']; H2=d['H2']; H4=d['H4']
def spectrum(p):
    Dq,B,C=p
    F2=49*B+5*C; F4=12.6*C
    H=Dq*Hcf+F2*H2+F4*H4
    q=np.linalg.eigvalsh(H[np.ix_(sec[3],sec[3])])
    s=np.linalg.eigvalsh(H[np.ix_(sec[1],sec[1])])
    dl=list(s)
    for x in q:
        i=int(np.argmin([abs(y-x) for y in dl])); dl.pop(i)
    return np.unique(np.round(q,4)), np.array(dl)
def quartet_rel(p):
    q,_=spectrum(p)
    return q-q[0]   # 4T1F, 4T2F, 4A2F, 4T1P  (distinct levels)
def triplets(p):
    _,dl=spectrum(p)
    # cluster
    out=[];i=0
    while i<len(dl):
        j=i
        while j+1<len(dl) and abs(dl[j+1]-dl[i])<1e-3: j+=1
        if j-i+1==3: out.append(dl[i])
        i=j+1
    return np.array(out)
obs=dict(T2=6150,A2=12400,T1P=16850)
def resid(p,k):
    qr=quartet_rel(p)
    tr=triplets(p)
    # doublet triplet energies relative to ground quartet
    q,_=spectrum(p); g=q[0]
    dtr=tr-g
    return np.array([qr[1]-6150, qr[2]-12400, qr[3]-16850, dtr[k]-19000 ])
if __name__=="__main__":
    p=(600,800,3000)
    q,dl=spectrum(p); print("quartets",q-q[0])
    print("triplets rel",triplets(p)-q[0])
EOF
python3 fit2.py