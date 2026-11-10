cd /dev/shm && cat << 'EOF' > fit.py
import numpy as np
from scipy.optimize import least_squares
HD,G2,G4,S2=np.load('mats.npy')
def levels(Dq,B,C):
    F2=49*(B+5*C/35); F4=441*C/35
    H=Dq*HD+F2*G2+F4*G4+1e-4*S2
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,S2,v)
    return w,np.round(s,3)
def singlets(Dq,B,C):
    w,s=levels(Dq,B,C)
    ws=w[np.abs(s)<0.01]
    # group degeneracies
    g=[];
    for x in ws:
        if g and abs(x-g[-1][0])<1e-3: g[-1][1]+=1
        else: g.append([x,1])
    return [(round(a-g[0][0],1),b) for a,b in g]
# free ion check
w,s=levels(0,1000,4000); print(sorted(set(np.round(w-w[0],0)))[:6])
print(singlets(2000,600,2400)[:8])
obs=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; L=singlets(Dq,B,4*B)
    e=[x for x,d in L if d==3][:3]
    return np.array(e)-obs
r=least_squares(res,[1900,600]); print(r.x,res(r.x))
Dq,B=r.x; print(singlets(Dq,B,4*B)[:10])
w,s=levels(Dq,B,4*B); print('ground S2',s[0])
EOF
python3 fit.py