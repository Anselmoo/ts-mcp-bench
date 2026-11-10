python3 - <<'EOF'
import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,_=np.load('mats.npy'); S2=np.load('S2.npy')
def lv(Dq,B,full=False):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]
    out=[];deg=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x);deg.append(1)
        else: deg[-1]+=1
    return (np.array(out)-out[0],deg) if full else np.array(out)-out[0]
obs=np.array([13960,22740,29700])
r=least_squares(lambda p: lv(*p)[1:4]-obs,[1600,780]); print(r.x,r.fun)
l,d=lv(*r.x,True); print(list(zip(np.round(l[:6]),d[:6])))
Dq,B=r.x
w,v=np.linalg.eigh(Dq*H1+B*(HB+4.5*HC)); s=np.diag(v.T@S2@v)
print([(round(w[i]-w[0]),round(s[i],2)) for i in range(25)])
print(Dq/B)
EOF