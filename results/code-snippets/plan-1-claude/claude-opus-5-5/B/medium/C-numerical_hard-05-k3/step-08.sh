python3 - <<'EOF'
import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,S2=np.load('mats.npy')
obs=np.array([13960,22740,29700])
def singlets(Dq,B):
    H=Dq*H1+B*HB+4.5*B*HC+ 1e3*B*0  
    # project singlets: add penalty to S2
    w,v=np.linalg.eigh(H+ 1e7*S2/ (1))
    w=w[w<5e6]
    w=w-w.min()
    # group degeneracies
    lv=[];deg=[]
    for x in w:
        if lv and abs(x-lv[-1])<1e-3: deg[-1]+=1
        else: lv.append(x);deg.append(1)
    return np.array(lv),deg
def res(p):
    lv,_=singlets(*p); return lv[1:4]-obs
r=least_squares(res,[2000,550]); print(r.x,res(r.x))
lv,deg=singlets(*r.x); print(list(zip(np.round(lv),deg))[:8])
# check ground is singlet overall
H=r.x[0]*H1+r.x[1]*(HB+4.5*HC); w,v=np.linalg.eigh(H); print(np.diag(v[:,:3].T@S2@v[:,:3]))
EOF