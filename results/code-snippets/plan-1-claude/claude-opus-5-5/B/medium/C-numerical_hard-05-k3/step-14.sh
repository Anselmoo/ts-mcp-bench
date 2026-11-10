python3 - <<'EOF'
import numpy as np
from scipy.optimize import least_squares
H1,HB,HC,S2=np.load('mats.npy')
N=H1.shape[0]
# fix: S2 stored = S-S+ + Sz^2 - Sz; need +Sz. recover Sz from diag? compute Sz from det list
import itertools
dets=list(itertools.combinations(range(10),6))
Sz=np.diag([sum(0.5 if p%2 else -0.5 for p in d) for d in dets])
S2=S2+2*Sz
print(np.unique(np.round(np.linalg.eigvalsh(S2),6)))
assert np.allclose(S2@HB,HB@S2) and np.allclose(S2@H1,H1@S2)
np.save('S2.npy',S2)
def lv(Dq,B):
    w=np.linalg.eigvalsh(Dq*H1+B*(HB+4.5*HC)+1e7*S2); w=w[w<5e6]; 
    out=[]
    for x in w:
        if not out or abs(x-out[-1])>1e-3: out.append(x)
    return np.array(out)-out[0]
obs=np.array([13960,22740,29700])
sols=set()
for Dq in np.arange(1000,4001,300):
  for B in np.arange(200,1501,100):
      r=least_squares(lambda p: lv(*p)[1:4]-obs,[Dq,B],bounds=([500,50],[8000,3000]))
      sols.add((round(r.x[0]),round(r.x[1]),round(np.sqrt(np.mean(r.fun**2)))))
for s in sorted(sols,key=lambda s:s[2])[:6]: print(s)
EOF